"""
Xovis SDK - Discovery & Multisensor Engine

This module resides within the State & Topology Plane, providing robust engines
for local network discovery, multisensor graph management, and resilient
fleet-wide bulk execution. It facilitates the orchestration of physical sensors
within virtual stitched environments.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from xovis.api.core.http import XovisHTTPClient
from xovis.api.device.cache import CacheCollection
from xovis.api.device.models import MSGraph, TopologyNodeInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DiscoveryPort(BaseModel):
    """Metadata for a discovered service port."""

    model_config = ConfigDict(extra="ignore")
    number: int
    service: str


class DiscoveryScanJob(BaseModel):
    """Payload for initiating a Layer 3 network scan."""

    model_config = ConfigDict(extra="ignore")
    first_ip: str
    count: int = 255


class DiscoverySensor(BaseModel):
    """Representation of a sensor discovered on the local network."""

    model_config = ConfigDict(extra="ignore")
    fw_version: str = ""
    group: str = ""
    ip: str = ""
    mac: str = ""
    model: str = ""
    name: str = ""
    ports: list[DiscoveryPort] = Field(default_factory=list)


class DiscoveryScanResult(BaseModel):
    """Container for discovery scan results."""

    model_config = ConfigDict(extra="ignore")
    sensors: list[DiscoverySensor] = Field(default_factory=list)


class MultisensorChildSensor(BaseModel):
    """Metadata for a physical child sensor within a multisensor context."""

    model_config = ConfigDict(extra="ignore")
    mac_address: str = ""
    name: str = ""
    group: str = ""
    ip_address: str = ""
    port: int = 80
    protocol: str = "http"
    username: str = "admin"
    status: str = "ok"


class MultisensorChildrenResponse(BaseModel):
    """Payload containing child sensors for a multisensor context."""

    model_config = ConfigDict(extra="ignore")
    sensors: list[MultisensorChildSensor] = Field(default_factory=list)


class BulkResult(BaseModel, Generic[T]):
    """
    Resilient return type for concurrent bulk execution operations.

    Isolates successes and exceptions to prevent a single offline sensor
    from crashing the orchestration pipeline.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    successes: list[T] = Field(default_factory=list)
    exceptions: list[Exception] = Field(default_factory=list)


class MultisensorContext:
    """
    Represents an isolated, virtual stitched environment on a host.

    Provides resource managers (DataPush, Scene, Analytics) bound to the
    virtual context and facilitates orchestration across physical child sensors.
    """

    def __init__(self, ms_id: int, name: str, parent_client: Any):
        """
        Initializes the MultisensorContext.

        Args:
            ms_id (int): The unique ID of the multisensor environment.
            name (str): The descriptive name of the context.
            parent_client (DeviceClient): The host device client instance.
        """
        self.ms_id = ms_id
        self.name = name
        self._parent_client = parent_client
        self._http_client: XovisHTTPClient = parent_client._http_client

        from xovis.api.device.resources.analytics import AnalyticsManager
        from xovis.api.device.resources.datapush import DataPushManager
        from xovis.api.device.resources.history import HistoryManager
        from xovis.api.device.resources.privacy import PrivacyManager
        from xovis.api.device.resources.scene import SceneManager
        from xovis.api.device.resources.system import SystemManager
        from xovis.api.device.resources.update import UpdateManager

        self.scene = SceneManager(parent_client, target_id=str(self.ms_id))
        self.datapush = DataPushManager(parent_client, target_id=str(self.ms_id))
        self.analytics = AnalyticsManager(parent_client, target_id=str(self.ms_id))
        self.history = HistoryManager(parent_client, target_id=str(self.ms_id))
        self.privacy = PrivacyManager(parent_client._http_client, parent_client, target_id=str(self.ms_id))
        self.update = UpdateManager(parent_client, target_id=str(self.ms_id))
        self.system = SystemManager(parent_client._http_client, parent_client, target_id=str(self.ms_id))

    async def get_child_clients(self) -> list[Any]:
        """
        Dynamically instantiates DeviceClient objects for mapped physical children.

        Returns:
            List[DeviceClient]: Collection of clients for physical sensors.
        """
        response = await self._http_client.get(f"/api/v5/multisensors/{self.ms_id}/sensors")
        payload = MultisensorChildrenResponse.model_validate(response.json())

        from xovis.api.device.client import DeviceClient

        clients = []
        for child in payload.sensors:
            client = DeviceClient(
                host=f"{child.protocol}://{child.ip_address}:{child.port}",
                username=child.username or self._parent_client._auth.username,
                password=self._parent_client._auth.password,
                use_ntlm=self._parent_client._auth.use_ntlm,
                timeout=self._http_client.client.timeout.read,
                max_retries=self._http_client.max_retries,
            )
            clients.append(client)
        return clients

    async def bulk_execute(self, func: Callable[[Any], Coroutine[Any, Any, T]]) -> BulkResult[T]:
        """
        Executes a concurrent functional bulk operation across all child cameras.

        Utilizes an asynchronous context manager for each child client to
        ensure strict connection pool management and resource cleanup.

        Args:
            func (Callable[[DeviceClient], Coroutine]): The async function to execute.

        Returns:
            BulkResult[T]: A report mapping successes and isolated exceptions.
        """
        children = await self.get_child_clients()

        async def wrap_execution(client: Any) -> T:
            async with client as c:
                return await func(c)

        tasks = [asyncio.create_task(wrap_execution(c)) for c in children]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        bulk = BulkResult[T]()
        for res in results:
            if isinstance(res, Exception):
                bulk.exceptions.append(res)
            else:
                bulk.successes.append(res)
        return bulk


class MultisensorsManager:
    """
    Manages the lifecycle and discovery of multisensors on a Host.
    """

    def __init__(self, parent_client: Any):
        """
        Initializes the MultisensorsManager.

        Args:
            parent_client (DeviceClient): The host device client instance.
        """
        self._parent_client = parent_client
        self._http_client = parent_client._http_client
        self._contexts: CacheCollection[MultisensorContext] = CacheCollection()

    async def sync(self) -> list[MultisensorContext]:
        """
        Fetches active multisensor environments to build isolated contexts.

        Populates the internal context cache for rapid dot-notation access.

        Returns:
            List[MultisensorContext]: The list of discovered multisensor contexts.
        """
        contexts = []
        try:
            # 1. Try the primary global status endpoint
            response = await self._http_client.get("/api/v5/multisensors/status")
            if response.status_code == 200:
                data = response.json()

                # The API returns a list under 'multisensors_status' or 'multisensors'
                ms_list = data.get("multisensors_status") or data.get("multisensors")

                if ms_list is None and isinstance(data, dict) and "multisensor_id" in data:
                    # Handle single-object response if it happens at this endpoint
                    ms_list = [data]

                if ms_list:
                    for ms in ms_list:
                        ms_id = ms.get("multisensor_id")
                        if ms_id is None:
                            ms_id = ms.get("id") or ms.get("custom_id")

                        if ms_id is not None:
                            name = ms.get("name") or f"Multisensor_{ms_id}"
                            ctx = MultisensorContext(ms_id=int(ms_id), name=name, parent_client=self._parent_client)
                            # Ensure we don't add duplicates from different keys
                            if not any(c.ms_id == ctx.ms_id for c in contexts):
                                contexts.append(ctx)

            # 2. Fallback/Probe: If no contexts found, try common IDs (e.g. 1)
            # to be robust against restrictive WAFs that might block the global status
            if not contexts:
                # We probe a wider range and check if they are actually active
                for probe_id in range(1, 6):
                    try:
                        probe_resp = await self._http_client.get(f"/api/v5/multisensors/{probe_id}/status", timeout=2.0)
                        if probe_resp.status_code == 200:
                            probe_data = probe_resp.json()
                            ms_id = probe_data.get("multisensor_id") or probe_id
                            name = probe_data.get("name") or f"Multisensor_{ms_id}"
                            contexts.append(MultisensorContext(ms_id=int(ms_id), name=name, parent_client=self._parent_client))
                    except Exception:
                        continue

            # CacheCollection expects a list of items during initialization
            self._contexts = CacheCollection(contexts)

            # Sync to the main ConfigCache
            if contexts:
                self._parent_client.cache.multisensors = contexts
        except Exception as e:
            logger.error(f"Multisensor sync failed: {e}")
            self._contexts = CacheCollection()

        return contexts

    @property
    def by_name(self) -> Any:
        """
        Exposes multisensor contexts via dot-notation REPL accessor.

        Returns:
            REPLAccessor[MultisensorContext]: The dynamic accessor facade.
        """
        return self._contexts.by_name


class TopologyManager:
    """
    Provides native Layer 2 and Layer 3 Local Network Discovery services.
    """

    def __init__(self, http_client: XovisHTTPClient, parent_client: Any):
        """
        Initializes the TopologyManager.

        Args:
            http_client (XovisHTTPClient): The Control Plane HTTP engine.
            parent_client (DeviceClient): The host device client instance.
        """
        self._http_client = http_client
        self._parent_client = parent_client

    def _instantiate_clients(self, sensors: list[DiscoverySensor]) -> list[Any]:
        """
        Factory for creating DeviceClient instances from discovery metadata.

        Args:
            sensors (List[DiscoverySensor]): Discovered sensor metadata.

        Returns:
            List[DeviceClient]: Initialized client instances.
        """
        from xovis.api.device.client import DeviceClient

        clients = []
        for sensor in sensors:
            port = sensor.ports[0].number if sensor.ports else 80
            scheme = sensor.ports[0].service if sensor.ports else "http"
            client = DeviceClient(
                host=f"{scheme}://{sensor.ip}:{port}",
                username=self._parent_client._auth.username,
                password=self._parent_client._auth.password,
                use_ntlm=self._parent_client._auth.use_ntlm,
                timeout=self._http_client.client.timeout.read,
                max_retries=self._http_client.max_retries,
            )
            clients.append(client)
        return clients

    async def localnetwork(self) -> list[Any]:
        """
        Performs passive Layer 2 Local Network Discovery.

        Returns:
            List[DeviceClient]: Collection of discovered sensor clients.
        """
        response = await self._http_client.get("/api/v5/discover/localnetwork")
        payload = DiscoveryScanResult.model_validate(response.json())
        return self._instantiate_clients(payload.sensors)

    async def scan(self, first_ip: str = "10.0.0.1", count: int = 255) -> list[Any]:
        """
        Performs active Layer 3 network scanning.

        Args:
            first_ip (str, optional): Starting IP address. Defaults to "10.0.0.1".
            count (int, optional): Number of addresses to scan. Defaults to 255.

        Returns:
            List[DeviceClient]: Collection of discovered sensor clients.
        """
        job = DiscoveryScanJob(first_ip=first_ip, count=count)
        response = await self._http_client.post("/api/v5/discover/scan", json=job)
        payload_res = DiscoveryScanResult.model_validate(response.json())
        return self._instantiate_clients(payload_res.sensors)

    async def get_ms_graph(self) -> MSGraph:
        """
        Synthesizes a Layer 2.5 directed graph of the multisensor cluster.

        Note:
            Xovis hardware uses a 'Top-Down' discovery model. Child sensors are 'ignorant'
            of their parent cluster. This method correctly synthesizes the hierarchy by
            cross-referencing Master status (enabled: true) with local network node discovery.

        Returns:
            MSGraph: The mapped topology with IP resolutions.
        """
        # Fetch multisensor status and network nodes concurrently
        ms_task = self._http_client.get("/api/v5/multisensors/status")
        discovery_task = self._http_client.get("/api/v5/discover/localnetwork")

        ms_resp, discovery_resp = await asyncio.gather(ms_task, discovery_task, return_exceptions=True)

        ms_data = []
        if not isinstance(ms_resp, Exception) and getattr(ms_resp, "status_code", 500) == 200:
            try:
                data = ms_resp.json()
                if isinstance(data, list):
                    ms_data = data
                else:
                    ms_data = data.get("multisensors_status") or data.get("multisensors") or []
                    if not ms_data and isinstance(data, dict) and "multisensor_id" in data:
                        ms_data = [data]
            except Exception as e:
                logging.warning(f"Failed to parse multisensor status JSON: {e}")
        elif isinstance(ms_resp, Exception):
            logging.warning(f"Failed to fetch multisensor status: {ms_resp}")

        # We also need the local IP mapping from discovery
        ip_map = {}
        if not isinstance(discovery_resp, Exception) and getattr(discovery_resp, "status_code", 500) == 200:
            try:
                discovery_data = DiscoveryScanResult.model_validate(discovery_resp.json())
                ip_map = {s.mac: s.ip for s in discovery_data.sensors}
            except Exception as e:
                logging.warning(f"Failed to parse discovery JSON: {e}")
        elif isinstance(discovery_resp, Exception):
            logging.warning(f"Failed to fetch discovery data: {discovery_resp}")

        children = []
        master_mac = ""
        alternative_masters = []

        # We aggregation children from ALL multisensor clusters to be robust
        seen_macs = set()
        for _i, ms in enumerate(ms_data):
            # Xovis API typically uses 'sensors', but some versions/contexts might use 'nodes'
            nodes = ms.get("sensors") or ms.get("nodes") or []
            logging.info(f"Parsing cluster '{ms.get('name')}' with {len(nodes)} nodes")

            cluster_master = ""
            for node in nodes:
                mac = node.get("mac_address") or node.get("mac")
                if not mac:
                    continue

                if node.get("reference"):
                    cluster_master = mac
                    if not master_mac:
                        master_mac = mac
                    elif mac != master_mac and mac not in alternative_masters:
                        alternative_masters.append(mac)

                if mac in seen_macs:
                    continue

                child = TopologyNodeInfo(
                    mac_address=mac,
                    ip_address=ip_map.get(mac) if mac else node.get("ip_address"),
                    name=node.get("name"),
                    group=node.get("group"),
                    status=node.get("status") or "ok",
                    reference=node.get("reference", False),
                )
                children.append(child)
                seen_macs.add(mac)

            if cluster_master:
                # If the cluster master is not the primary master_mac, it's an alternative
                if cluster_master != master_mac and cluster_master not in alternative_masters:
                    alternative_masters.append(cluster_master)

        return MSGraph(
            master_mac=master_mac,
            children=children,
            ip_map=ip_map,
            alternative_masters=alternative_masters,
        )
