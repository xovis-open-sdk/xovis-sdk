"""
Xovis SDK - Device Configuration Cache Manager

This module resides within the State & Topology Plane, providing a stateful,
graph-aware synchronization engine for edge sensor configurations. It implements
the `ConfigCacheManager` which abstracts complex nested topologies into
convenient, dot-notation accessors for Jupyter/REPL environments.
"""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from xovis.api.core.exceptions import XovisClientError
from xovis.api.core.http import XovisHTTPClient
from xovis.api.device.discovery import discovery_manager
from xovis.api.device.models import CacheStrategy, TopologyNodeInfo
from xovis.config import config

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CachePaths:
    """Helper namespace providing autocomplete and auto-suggestions for all local resources."""

    BASE_DIR = Path("_local_resources")
    STATES_DIR = BASE_DIR / "states"
    SCHEMAS_DIR = BASE_DIR / "schemas"
    SAMPLES_DIR = BASE_DIR / "samples"

    DEVICE_STATE = STATES_DIR / "device_state.json"
    FLEET_STATE = STATES_DIR / "hub_fleet_state.json"

    @classmethod
    def get_system_cache_dir(cls) -> Path:
        """Resolves the system-level global cache directory in a platform-independent manner.

        Returns:
            Path: The resolved path to the system cache directory.
        """
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / "xovis" / "Cache"
            return Path.home() / "AppData" / "Local" / "xovis" / "Cache"
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / "xovis"
        return Path.home() / ".cache" / "xovis"

    @classmethod
    def list_available_states(cls) -> list[str]:
        """Discovers all available local state files. Highly useful in REPL/Notebooks.

        Returns:
            list[str]: Filenames of all available local states.
        """
        states = []
        if cls.STATES_DIR.exists():
            states.extend([f.name for f in cls.STATES_DIR.glob("*.json")])

        sys_states_dir = cls.get_system_cache_dir() / "states"
        if sys_states_dir.exists():
            states.extend([f.name for f in sys_states_dir.glob("*.json")])

        return sorted(list(set(states)))

    @classmethod
    def get_latest_state(cls) -> Path:
        """Helper to get the most recently modified state cache for quick debugging.

        Returns:
            Path: The Path to the most recently modified state cache, falling back to DEVICE_STATE.
        """
        candidates = []

        if cls.STATES_DIR.exists():
            candidates.extend(cls.STATES_DIR.glob("*.json"))

        sys_states_dir = cls.get_system_cache_dir() / "states"
        if sys_states_dir.exists():
            candidates.extend(sys_states_dir.glob("*.json"))

        candidates.extend([cls.DEVICE_STATE, cls.FLEET_STATE])

        existing = [p for p in candidates if p.exists()]
        if not existing:
            return cls.DEVICE_STATE
        return max(existing, key=lambda p: p.stat().st_mtime)


class REPLAccessor(Generic[T]):
    """
    Read-only dynamic accessor allowing object discovery via dot-notation.

    This utility provides a hyper-optimized developer experience in interactive
    environments (Jupyter/REPL) by mapping resource names to object attributes
    using robust regex sanitization.
    """

    def __init__(self, elements: list[T], key_attr: str = "name"):
        """
        Initializes the REPLAccessor with a list of elements.

        Args:
            elements (List[T]): The collection of resources to expose.
            key_attr (str, optional): The attribute used for mapping (e.g., "name", "id").
                Defaults to "name".
        """
        self._items = {}
        for item in elements:
            key = getattr(item, key_attr, None)
            if key is not None:
                key = str(key)
                safe_key = re.sub(r"\W+", "_", key).strip("_")
                if safe_key and safe_key[0].isdigit():
                    safe_key = f"_{safe_key}"
                self._items[safe_key] = item
                if key != safe_key:
                    self._items[key] = item

    def __getattr__(self, name: str) -> T:
        """
        Retrieves a resource via dot-notation.

        Args:
            name (str): The sanitized or raw name of the resource.

        Returns:
            T: The mapped resource element.

        Raises:
            AttributeError: If the resource name is not found in the accessor.
        """
        if name in self._items:
            return self._items[name]
        raise AttributeError(f"Resource '{name}' not found. Available: {list(self._items.keys())}")

    def __getitem__(self, key: str) -> T:
        """
        Retrieves a resource via bracket-notation.

        Args:
            key (str): The sanitized or raw name of the resource.

        Returns:
            T: The mapped resource element.

        Raises:
            KeyError: If the resource name is not found in the accessor.
        """
        if key in self._items:
            return self._items[key]
        raise KeyError(f"Resource '{key}' not found. Available: {list(self._items.keys())}")

    def __dir__(self) -> list[str]:
        """
        Enables IDE/REPL auto-completion for mapped resources.

        Returns:
            List[str]: Combined list of class members and dynamic resource keys.
        """
        return list(super().__dir__()) + list(self._items.keys())

    def __repr__(self) -> str:
        """
        Returns a string representation of the REPLAccessor.

        Returns:
            str: Description of available resources.
        """
        return f"<REPLAccessor resources={list(self._items.keys())}>"


class CacheCollection(list, Generic[T]):
    """
    Enhanced list subclass exposing REPL accessors.

    Wraps standard lists with `.by_name` and `.by_id` properties to facilitate
    rapid resource discovery in the State & Topology Plane.
    """

    def __init__(self, items: Optional[list[T]] = None):
        """
        Initializes the CacheCollection.

        Args:
            items (Optional[List[T]], optional): Initial list of elements. Defaults to None.
        """
        super().__init__()
        if items:
            self.extend(items)

    @property
    def by_name(self) -> REPLAccessor[T]:
        """
        Exposes elements via their 'name' attribute for dot-notation access.

        Returns:
            REPLAccessor[T]: A name-mapped dynamic accessor facade.
        """
        return REPLAccessor(self, key_attr="name")

    @property
    def by_id(self) -> REPLAccessor[T]:
        """
        Exposes elements via their 'id' attribute for dot-notation access.

        Returns:
            REPLAccessor[T]: An ID-mapped dynamic accessor facade.
        """
        return REPLAccessor(self, key_attr="id")


def _by_name_property(self) -> REPLAccessor:
    """
    Safely extracts lists from Pydantic V2 Models or RootModels for REPL access.

    This helper is monkey-patched onto auto-generated models to provide
    the `.by_name` accessor pattern consistently.

    Returns:
        REPLAccessor: A dynamic accessor for the identified collection.
    """
    keys_to_check = [
        "agents",
        "connections",
        "geometries",
        "logics",
        "modifiers",
        "counters",
        "scene_masks",
        "layers",
        "root",
    ]
    for key in keys_to_check:
        if hasattr(self, key):
            return REPLAccessor(getattr(self, key))
    return REPLAccessor([])


from xovis.models.device_auto import (
    AgentConfigCollection,
    ConnectionConfigCollection,
    CounterCollection,
    LogicCollection,
    ModifierCollection,
    SceneGeometries,
)

AgentConfigCollection.by_name = property(_by_name_property)
ConnectionConfigCollection.by_name = property(_by_name_property)
SceneGeometries.by_name = property(_by_name_property)
LogicCollection.by_name = property(_by_name_property)
ModifierCollection.by_name = property(_by_name_property)
CounterCollection.by_name = property(_by_name_property)


class CacheResource(BaseModel):
    """
    Lightweight Pydantic model for cached resource metadata.
    """

    model_config = ConfigDict(extra="allow")
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None


class ContextStateBucket(BaseModel):
    """
    Isolated state container for a specific lens context or virtual environment.

    Partitions resources (agents, connections, geometries, etc.) by their
    operational context to prevent configuration leakage between physical
    sensors ("singlesensor") and virtual stitched environments ("multisensor").
    """

    model_config = ConfigDict(extra="ignore")
    agents: list[CacheResource] = Field(default_factory=list)
    connections: list[CacheResource] = Field(default_factory=list)
    zones: list[CacheResource] = Field(default_factory=list)
    lines: list[CacheResource] = Field(default_factory=list)
    logics: list[CacheResource] = Field(default_factory=list)
    modifiers: list[CacheResource] = Field(default_factory=list)
    counters: list[CacheResource] = Field(default_factory=list)
    masks: list[CacheResource] = Field(default_factory=list)
    layers: list[CacheResource] = Field(default_factory=list)
    child_sensors: list[TopologyNodeInfo] = Field(default_factory=list)


class HostStateBucket(BaseModel):
    """
    Root state container for the entire physical device host.

    Aggregates checksum metadata and partitioned context buckets to represent
    the complete topology of a Xovis sensor or Spider NUC.
    """

    model_config = ConfigDict(extra="ignore")
    checksum: Optional[str] = None
    contexts: dict[str, ContextStateBucket] = Field(default_factory=dict)


class BulkDeviceFacade:
    """Dynamic broadcasting facade that executes operations concurrently across child managers."""

    def __init__(self, child_clients: list[Any], manager_attr: str):
        """Initializes the BulkDeviceFacade.

        Args:
            child_clients (list[Any]): List of child DeviceClient instances.
            manager_attr (str): The name of the manager attribute.
        """
        self._child_clients = child_clients
        self._manager_attr = manager_attr

    def __getattr__(self, name: str) -> Any:
        """Intercepts method calls and broadcasts them concurrently to all child managers.

        Args:
            name (str): The method name to execute.

        Returns:
            Callable[..., Coroutine]: The broadcasting async method wrapper.
        """

        async def broadcast_call(*args: Any, **kwargs: Any) -> Any:
            from xovis.api.device.topology import BulkResult

            async def single_call(client: Any) -> Any:
                async with client as c:
                    manager = getattr(c, self._manager_attr)
                    method = getattr(manager, name)
                    return await method(*args, **kwargs)

            tasks = [asyncio.create_task(single_call(c)) for c in self._child_clients]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            bulk = BulkResult()
            for res in results:
                if isinstance(res, Exception):
                    bulk.exceptions.append(res)
                else:
                    bulk.successes.append(res)
            return bulk

        return broadcast_call


class ChildDevicesAccessor:
    """Smart accessor bridging individual child lookups with grouped/bulk execution."""

    def __init__(self, parent_context: Any, child_clients: list[Any]):
        """Initializes the ChildDevicesAccessor.

        Args:
            parent_context (Any): The parent ContextAccessor.
            child_clients (list[Any]): Mapped physical child clients.
        """
        self._parent_context = parent_context
        self._child_clients = child_clients
        self.by_name = REPLAccessor(child_clients, key_attr="name")

    @property
    def connections(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens connections from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined connection configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.connections)
        return CacheCollection(merged)

    @property
    def zones(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens scene zones from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined zone configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.zones)
        return CacheCollection(merged)

    @property
    def lines(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens scene lines from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined line configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.lines)
        return CacheCollection(merged)

    @property
    def agents(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens agents from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined agent configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.agents)
        return CacheCollection(merged)

    @property
    def logics(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens logics from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined logic configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.logics)
        return CacheCollection(merged)

    @property
    def modifiers(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens modifiers from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined modifier configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.modifiers)
        return CacheCollection(merged)

    @property
    def counters(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens counters from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined counter configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.counters)
        return CacheCollection(merged)

    @property
    def masks(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens masks from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined mask configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.masks)
        return CacheCollection(merged)

    @property
    def layers(self) -> CacheCollection[CacheResource]:
        """Aggregates and flattens layers from all physical child caches.

        Returns:
            CacheCollection[CacheResource]: Combined layer configurations.
        """
        merged = []
        for client in self._child_clients:
            merged.extend(client.cache.singlesensor.layers)
        return CacheCollection(merged)

    def __getattr__(self, name: str) -> Any:
        """Provides direct access to bulk managers.

        Args:
            name (str): Attribute name to delegate.

        Returns:
            Any: BulkDeviceFacade wrapping the target manager attribute.

        Raises:
            AttributeError: If the manager is not a standard supported device manager.
        """
        standard_managers = {
            "images",
            "privacy",
            "scene",
            "datapush",
            "analytics",
            "history",
            "update",
            "system",
            "network",
            "time",
            "itxpt",
            "users",
        }
        if name in standard_managers:
            return BulkDeviceFacade(self._child_clients, name)
        raise AttributeError(f"Attribute '{name}' not found on ChildDevicesAccessor.")


class ContextAccessor:
    """
    Facade providing high-level access to a ContextStateBucket.

    Wraps raw state buckets in `CacheCollection` instances to enable
    dot-notation resource discovery (e.g., `ctx.agents.by_name.MyAgent`).
    """

    def __init__(self, bucket: ContextStateBucket, name: Optional[str] = None, parent_client: Optional[Any] = None):
        """
        Initializes the ContextAccessor for a specific bucket.

        Args:
            bucket (ContextStateBucket): The raw state bucket to wrap.
            name (Optional[str]): Descriptive name for the context.
            parent_client (Optional[Any]): The host device client instance.
        """
        self._bucket = bucket
        self.name = name
        self._parent_client = parent_client

    @property
    def child_devices(self) -> ChildDevicesAccessor:
        """Provides instant autosuggestion/REPL access to physical child clients.

        Returns:
            ChildDevicesAccessor: High-level child client and bulk operations accessor.
        """
        from xovis.api.device.client import DeviceClient

        clients = []
        sensors = getattr(self._bucket, "child_sensors", []) or []
        for sensor in sensors:
            if not sensor.ip_address:
                continue
            username = "admin"
            password = ""
            use_ntlm = False
            if self._parent_client:
                username = self._parent_client._auth.username
                password = self._parent_client._auth.password
                use_ntlm = self._parent_client._auth.use_ntlm

            client = DeviceClient(
                host=sensor.ip_address,
                username=username,
                password=password,
                use_ntlm=use_ntlm,
                cache_child_devices=False,
            )
            client.name = sensor.name or f"sensor_{sensor.mac_address.replace(':', '_')}"
            clients.append(client)

        return ChildDevicesAccessor(self, clients)

    @property
    def child_caches(self) -> REPLAccessor["ContextAccessor"]:
        """Provides REPL access to the offline-first cache states of those child sensors.

        Returns:
            REPLAccessor[ContextAccessor]: Facade for child configurations.
        """
        caches = []
        child_devs = self.child_devices
        for client in child_devs._child_clients:
            accessor = ContextAccessor(client.cache.singlesensor._bucket, name=client.name, parent_client=client)
            caches.append(accessor)
        return REPLAccessor(caches, key_attr="name")

    def __repr__(self) -> str:
        """
        Returns a string representation of the ContextAccessor.

        Returns:
            str: Description of the context.
        """
        return f"<ContextAccessor name='{self.name}'>"

    @property
    def agents(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached DataPush agents.

        Returns:
            CacheCollection[CacheResource]: Collection of agent metadata.
        """
        return CacheCollection(self._bucket.agents)

    @agents.setter
    def agents(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached DataPush agents."""
        self._bucket.agents = value

    @property
    def connections(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached DataPush connections.

        Returns:
            CacheCollection[CacheResource]: Collection of connection metadata.
        """
        return CacheCollection(self._bucket.connections)

    @connections.setter
    def connections(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached DataPush connections."""
        self._bucket.connections = value

    @property
    def zones(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached scene zones.

        Returns:
            CacheCollection[CacheResource]: Collection of zone metadata.
        """
        return CacheCollection(self._bucket.zones)

    @zones.setter
    def zones(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached scene zones."""
        self._bucket.zones = value

    @property
    def lines(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached scene lines.

        Returns:
            CacheCollection[CacheResource]: Collection of line metadata.
        """
        return CacheCollection(self._bucket.lines)

    @lines.setter
    def lines(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached scene lines."""
        self._bucket.lines = value

    @property
    def logics(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached analysis logics.

        Returns:
            CacheCollection[CacheResource]: Collection of logic metadata.
        """
        return CacheCollection(self._bucket.logics)

    @logics.setter
    def logics(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached analysis logics."""
        self._bucket.logics = value

    @property
    def modifiers(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached analysis modifiers.

        Returns:
            CacheCollection[CacheResource]: Collection of modifier metadata.
        """
        return CacheCollection(self._bucket.modifiers)

    @modifiers.setter
    def modifiers(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached analysis modifiers."""
        self._bucket.modifiers = value

    @property
    def counters(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached analysis counters.

        Returns:
            CacheCollection[CacheResource]: Collection of counter metadata.
        """
        return CacheCollection(self._bucket.counters)

    @counters.setter
    def counters(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached analysis counters."""
        self._bucket.counters = value

    @property
    def masks(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached scene masks.

        Returns:
            CacheCollection[CacheResource]: Collection of mask metadata.
        """
        return CacheCollection(self._bucket.masks)

    @masks.setter
    def masks(self, value: Optional[list[CacheResource]]) -> None:
        """Sets the cached scene masks."""
        self._bucket.masks = value

    @property
    def layers(self) -> CacheCollection[CacheResource]:
        """
        Accesses the cached scene layers.

        Returns:
            CacheCollection[CacheResource]: Collection of layer metadata.
        """
        return CacheCollection(self._bucket.layers)


class ConfigCacheManager:
    """
    Stateful Configuration Synchronizer and Topology Graph Manager.

    Coordinates the background polling of edge sensor state hashes and performs
    concurrent synchronization of the full configuration graph. Implements
    GC protection for long-running background tasks and partitions state
    by physical and virtual contexts.
    """

    def __init__(
        self,
        http_client: XovisHTTPClient,
        strategy: CacheStrategy,
        ttl_seconds: float,
        poll_interval: float,
        auto_persist_path: Optional[str] = None,
        persistence_dir: Optional[str] = None,
        cache_child_devices: bool = False,
    ):
        """
        Initializes the ConfigCacheManager.

        Args:
            http_client (XovisHTTPClient): The Control Plane HTTP engine.
            strategy (CacheStrategy): The synchronization strategy (MANUAL, LAZY, or BACKGROUND).
            ttl_seconds (float): Time-to-live for cached entries.
            poll_interval (float): Frequency of background state checks.
            auto_persist_path (Optional[str], optional): Path to a JSON file for
                offline-first state persistence. Defaults to None.
            persistence_dir (Optional[str], optional): Path to a directory for
                automated state persistence. Defaults to None.
            cache_child_devices (bool, optional): Whether to recursively cache child devices. Defaults to False.
        """
        self._http_client = http_client
        self.strategy = strategy
        self.ttl_seconds = ttl_seconds
        self.poll_interval = poll_interval
        self.auto_persist_path = auto_persist_path
        self.persistence_dir = persistence_dir
        self.cache_child_devices = cache_child_devices

        self._background_tasks: set[asyncio.Task] = set()
        self._is_running = False
        self._parent_client: Optional[Any] = None

        self._state = HostStateBucket()

    @property
    def singlesensor(self) -> ContextAccessor:
        """
        Accessor for the physical lens context.

        Returns:
            ContextAccessor: Facade for the 'singlesensor' state bucket.
        """
        bucket = self._state.contexts.setdefault("singlesensor", ContextStateBucket())
        return ContextAccessor(bucket, name="singlesensor", parent_client=self._parent_client)

    @property
    def multisensors(self) -> REPLAccessor[ContextAccessor]:
        """
        Dynamic accessor for virtual stitched environments (Multisensors).

        Returns:
            REPLAccessor[ContextAccessor]: Mapped context IDs to state facades.
        """
        accessors = []
        for cid, cb in self._state.contexts.items():
            if cid == "singlesensor":
                continue
            accessors.append(ContextAccessor(cb, name=str(cid), parent_client=self._parent_client))

        return REPLAccessor(accessors, key_attr="name")

    @multisensors.setter
    def multisensors(self, contexts: list[Any]) -> None:
        """
        Updates the internal state buckets from discovered multisensor contexts.

        Args:
            contexts (List[MultisensorContext]): The list of discovered contexts.
        """
        # We preserve the 'singlesensor' bucket if it exists
        new_contexts = {}
        if "singlesensor" in self._state.contexts:
            new_contexts["singlesensor"] = self._state.contexts["singlesensor"]

        for ctx in contexts:
            ms_id = str(ctx.ms_id)
            # Carry over existing data if we already had a bucket for this ID
            if ms_id in self._state.contexts:
                new_contexts[ms_id] = self._state.contexts[ms_id]
            else:
                new_contexts[ms_id] = ContextStateBucket()

        self._state.contexts = new_contexts

    @property
    def buckets(self) -> REPLAccessor[ContextAccessor]:
        """
        Unified accessor for all state buckets (physical and virtual).

        Returns:
            REPLAccessor[ContextAccessor]: All contexts mapped by their ID/name.
        """
        accessors = []
        for cid, cb in self._state.contexts.items():
            accessors.append(ContextAccessor(cb, name=str(cid), parent_client=self._parent_client))
        return REPLAccessor(accessors, key_attr="name")

    @property
    def agents(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.agents."""
        return self.singlesensor.agents

    @property
    def connections(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.connections."""
        return self.singlesensor.connections

    @property
    def zones(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.zones."""
        return self.singlesensor.zones

    @property
    def lines(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.lines."""
        return self.singlesensor.lines

    @property
    def geometries(self) -> CacheCollection[CacheResource]:
        """
        Legacy shim combining zones and lines from the singlesensor context.

        Returns:
            CacheCollection[CacheResource]: Combined collection of zones and lines.
        """
        return CacheCollection(list(self.zones) + list(self.lines))

    @property
    def logics(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.logics."""
        return self.singlesensor.logics

    @property
    def modifiers(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.modifiers."""
        return self.singlesensor.modifiers

    @property
    def counters(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.counters."""
        return self.singlesensor.counters

    @property
    def masks(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.masks."""
        return self.singlesensor.masks

    @property
    def layers(self) -> CacheCollection[CacheResource]:
        """Legacy shim mapping to singlesensor.layers."""
        return self.singlesensor.layers

    async def start(self) -> None:
        """
        Starts the background configuration watcher.

        Performs an initial synchronization and spawns a background loop with
        hard-referenced tasks to prevent mid-execution garbage collection.
        Also handles auto-loading from disk if persistence is enabled.
        """
        if self.auto_persist_path:
            try:
                await self.load_from_disk()
            except Exception as e:
                logger.warning(f"Failed to load cache from disk: {e}")

        is_watcher = getattr(self.strategy, "value", str(self.strategy)) == "BACKGROUND_WATCHER"
        if config.CACHE_ENABLED or is_watcher:
            if not self._is_running:
                self._is_running = True

                await self.sync()

                task = asyncio.create_task(self._watcher_loop())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def stop(self) -> None:
        """
        Cleanly halts background synchronization loops.

        Ensures all tasks are cancelled and awaited to prevent socket leaks.
        """
        self._is_running = False
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    async def _watcher_loop(self) -> None:
        """
        Polls the API config state hash for remote mutations.

        Triggered by the BACKGROUND_WATCHER strategy. If a checksum change is
        detected, initiates a full graph synchronization.
        """
        interval = self.poll_interval if self.poll_interval else config.POLL_INTERVAL_SECONDS
        while self._is_running:
            try:
                await asyncio.sleep(interval)
                response = await self._http_client.get("/api/v5/config/state")
                data = response.json()

                new_checksum = data.get("state", {}).get("checksum", data.get("checksum"))

                if new_checksum and new_checksum != self._state.checksum:
                    logger.info(f"Configuration change detected (checksum: {new_checksum}). Syncing cache...")
                    self._state.checksum = new_checksum
                    await self.sync()

                    if self.auto_persist_path or self.persistence_dir:
                        await self.save_to_disk()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Background watcher failed to sync: {e}")

    async def sync(self) -> None:
        """
        Pulls the entire topology graph concurrently, isolating each context.

        Performs multisensor discovery, builds a concurrent task matrix for all
        endpoints (DataPush, Scene, Analytics), and populates partitioned
        state buckets.

        Raises:
            Exception: Logged as an error if the synchronization fails.
        """
        try:
            contexts_to_sync = ["singlesensor"]
            try:
                ms_resp = await self._http_client.get("/api/v5/multisensors/status")
                ms_status = ms_resp.json()
                if isinstance(ms_status, list):
                    for ms in ms_status:
                        if "id" in ms:
                            contexts_to_sync.append(str(ms["id"]))
            except (XovisClientError, Exception) as e:
                logger.debug(f"Multisensor discovery skipped: {e}")

            tasks = []
            context_map = []

            endpoints = [
                ("agents", "/data/push/agents"),
                ("connections", "/data/push/connections"),
                ("geometries", "/scene/geometries"),
                ("logics", "/analysis/logics"),
                ("modifiers", "/analysis/modifiers"),
                ("counters", "/analysis/counters"),
                ("scene_masks", "/scene/masks"),
                ("layers", "/scene/layers"),
            ]

            for ctx in contexts_to_sync:
                prefix = f"/api/v5/multisensors/{ctx}" if ctx != "singlesensor" else "/api/v5/singlesensor"
                for _, ep in endpoints:
                    tasks.append(self._http_client.get(f"{prefix}{ep}"))
                context_map.append(ctx)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            stride = len(endpoints)
            for i, ctx in enumerate(context_map):
                ctx_results = results[i * stride : (i + 1) * stride]
                bucket = ContextStateBucket()

                def extract_data(res, key, entity_name=None, endpoint=None):
                    if isinstance(res, Exception):
                        return []
                    try:
                        data = res.json()
                        raw_items = data.get(key, data.get("root", []))

                        # Discovery Crawler: Capture unknown fields
                        if entity_name and raw_items and isinstance(raw_items, list):
                            known_fields = CacheResource.model_fields.keys()
                            for item in raw_items:
                                if isinstance(item, dict):
                                    discovery_manager.capture(
                                        entity_name=entity_name,
                                        raw_data=item,
                                        known_fields=set(known_fields),
                                        endpoint=endpoint,
                                    )
                        return raw_items
                    except Exception:
                        return []

                bucket.agents = [
                    CacheResource.model_validate(a) for a in extract_data(ctx_results[0], "agents", "Agent", f"{prefix}/data/push/agents")
                ]
                bucket.connections = [
                    CacheResource.model_validate(c)
                    for c in extract_data(
                        ctx_results[1],
                        "connections",
                        "Connection",
                        f"{prefix}/data/push/connections",
                    )
                ]

                geoms_data = extract_data(ctx_results[2], "geometries", "Geometry", f"{prefix}/scene/geometries")
                geoms = [CacheResource.model_validate(g) for g in geoms_data]
                bucket.zones = [g for g in geoms if g.type == "ZONE"]
                bucket.lines = [g for g in geoms if g.type == "LINE"]

                bucket.logics = [
                    CacheResource.model_validate(l) for l in extract_data(ctx_results[3], "logics", "Logic", f"{prefix}/analysis/logics")
                ]
                bucket.modifiers = [
                    CacheResource.model_validate(m) for m in extract_data(ctx_results[4], "modifiers", "Modifier", f"{prefix}/analysis/modifiers")
                ]
                bucket.counters = [
                    CacheResource.model_validate(c) for c in extract_data(ctx_results[5], "counters", "Counter", f"{prefix}/analysis/counters")
                ]
                bucket.masks = [
                    CacheResource.model_validate(sm) for sm in extract_data(ctx_results[6], "scene_masks", "Mask", f"{prefix}/scene/masks")
                ]
                bucket.layers = [CacheResource.model_validate(ly) for ly in extract_data(ctx_results[7], "layers", "Layer", f"{prefix}/scene/layers")]

                self._state.contexts[ctx] = bucket

            ms_contexts = [ctx for ctx in context_map if ctx != "singlesensor"]
            if ms_contexts:
                sensor_tasks = [self._http_client.get(f"/api/v5/multisensors/{ctx}/sensors") for ctx in ms_contexts]
                sensor_results = await asyncio.gather(*sensor_tasks, return_exceptions=True)
                for ctx, res in zip(ms_contexts, sensor_results):
                    if not isinstance(res, Exception) and res.status_code == 200:
                        try:
                            from xovis.api.device.topology import MultisensorChildrenResponse

                            payload = MultisensorChildrenResponse.model_validate(res.json())
                            self._state.contexts[ctx].child_sensors = [
                                TopologyNodeInfo(
                                    mac_address=child.mac_address,
                                    ip_address=child.ip_address,
                                    name=child.name,
                                    group=child.group,
                                    status=child.status,
                                )
                                for child in payload.sensors
                            ]
                        except Exception as e:
                            logger.debug(f"Failed parsing child sensors for context {ctx}: {e}")

            if self.cache_child_devices:
                from xovis.api.device.client import DeviceClient

                child_sync_tasks = []
                for ctx in ms_contexts:
                    bucket = self._state.contexts.get(ctx)
                    if bucket and bucket.child_sensors:
                        for sensor in bucket.child_sensors:
                            if not sensor.ip_address:
                                continue
                            username = "admin"
                            password = ""
                            use_ntlm = False
                            if self._parent_client:
                                username = self._parent_client._auth.username
                                password = self._parent_client._auth.password
                                use_ntlm = self._parent_client._auth.use_ntlm
                            child_client = DeviceClient(
                                host=sensor.ip_address,
                                username=username,
                                password=password,
                                use_ntlm=use_ntlm,
                                cache_child_devices=False,
                            )
                            child_sync_tasks.append(child_client.cache.sync())
                if child_sync_tasks:
                    await asyncio.gather(*child_sync_tasks, return_exceptions=True)

            if True:
                await self.save_to_disk()

        except Exception as e:
            logger.error(f"Failed to synchronize cache: {e}")

    def export_to_file(self, file_path: str) -> None:
        """
        Exports the entire nested state graph to a JSON file.

        Args:
            file_path (str): The destination file path.
        """
        with open(file_path, "w") as f:
            f.write(self._state.model_dump_json())

    def load_from_file(self, file_path: str) -> None:
        """
        Loads a nested state graph from a JSON file into memory.

        Args:
            file_path (str): The source JSON file path.
        """
        with open(file_path) as f:
            self._state = HostStateBucket.model_validate_json(f.read())

    def _ensure_directory_or_fallback(self, path: Path) -> Optional[Path]:
        """Ensures the directory for the given path is writeable or falls back.

        Implements the 3-Tier cache folder creation and fallback strategy.

        Args:
            path (Path): The desired target file path.

        Returns:
            Optional[Path]: The writeable target path, or None if falling back
                to memory-only.
        """
        if getattr(self, "_memory_only", False):
            return None

        parent = path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            return path
        except (PermissionError, OSError) as exc:
            logger.warning(f"Local directory creation failed at {parent} ({exc}). Attempting global system cache fallback.")

        try:
            try:
                rel_parts = path.relative_to(CachePaths.BASE_DIR)
                sys_target = CachePaths.get_system_cache_dir() / rel_parts
            except ValueError:
                sys_target = CachePaths.get_system_cache_dir() / path.name

            sys_parent = sys_target.parent
            sys_parent.mkdir(parents=True, exist_ok=True)
            return sys_target
        except (PermissionError, OSError) as exc:
            logger.warning(
                f"Unable to write to system-level cache workspace ({exc}). "
                f"Falling back to temporary memory-only caching. "
                f"To persist cache, ensure write permissions exist."
            )

        self._memory_only = True
        return None

    async def _resolve_persist_path(self) -> Optional[str]:
        """Resolves the final persistence path, dynamically if persistence_dir is used.

        Returns:
            Optional[str]: The absolute path to the state file, or None.
        """
        if getattr(self, "_memory_only", False):
            return None

        from urllib.parse import urlparse

        parsed = urlparse(str(self._http_client.base_url))
        host = parsed.netloc or parsed.path
        host_clean = host.split(":")[0].replace(".", "_").replace(":", "_")

        resolved_path: Optional[Path] = None

        if self.auto_persist_path:
            resolved_path = Path(self.auto_persist_path)
        elif self.persistence_dir:
            try:
                resp = await self._http_client.get("/api/v5/device/info")
                info = resp.json()
                mac = info.get("macAddress", "unknown").replace(":", "-")
                resolved_path = Path(self.persistence_dir) / f"{mac}.json"
            except Exception as e:
                logger.warning(f"Could not resolve dynamic persistence path: {e}")
                return None
        else:
            host_state_path = CachePaths.STATES_DIR / f"state_{host_clean}.json"
            device_state_path = CachePaths.DEVICE_STATE

            if host_state_path.exists():
                resolved_path = host_state_path
            elif device_state_path.exists():
                resolved_path = device_state_path
            else:
                resolved_path = host_state_path

        if resolved_path:
            final_path = self._ensure_directory_or_fallback(resolved_path)
            return str(final_path) if final_path else None

        return None

    async def save_to_disk(self) -> None:
        """
        Safely serializes the HostStateBucket to disk.

        Uses asyncio.to_thread to prevent blocking the event loop during
        file I/O.
        """
        path = await self._resolve_persist_path()
        if not path:
            return

        def _save():
            with open(path, "w") as f:
                f.write(self._state.model_dump_json(indent=2))

        await asyncio.to_thread(_save)

    async def load_from_disk(self) -> None:
        """
        Deserializes the HostStateBucket from disk.

        Uses asyncio.to_thread to prevent blocking the event loop during
        file I/O.
        """
        path = await self._resolve_persist_path()
        if not path:
            return

        import os

        if not await asyncio.to_thread(os.path.exists, path):
            return

        def _load():
            with open(path) as f:
                return f.read()

        data = await asyncio.to_thread(_load)
        self._state = HostStateBucket.model_validate_json(data)
