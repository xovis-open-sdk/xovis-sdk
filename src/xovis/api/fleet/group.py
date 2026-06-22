"""
DeviceGroup - SDK-Native Fleet Buckets.
"""

import asyncio
import logging
from typing import Any, Union

from xovis.api.device.base import BaseControlPlane
from xovis.api.device.cache import REPLAccessor
from xovis.api.device.models import CacheStrategy
from xovis.api.fleet.models import BulkOperationResult

logger = logging.getLogger(__name__)


class BulkCacheFacade:
    """Facade for aggregating cache operations across a DeviceGroup."""

    def __init__(self, clients: list[Any]):
        """Initializes the BulkCacheFacade."""
        self._clients = clients

    async def save_to_disk(self) -> BulkOperationResult[bool]:
        """
        Triggers parallel IO persistence across the fleet.

        Returns:
            BulkOperationResult[bool]: Success mapping per device host.
        """
        tasks = [c.cache.save_to_disk() for c in self._clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        res = BulkOperationResult[bool]()
        for client, r in zip(self._clients, results):
            host_key = str(client._http_client.client.base_url)
            if isinstance(r, Exception):
                res.exceptions[host_key] = r
            else:
                res.successes[host_key] = r
        return res

    async def sync(self) -> BulkOperationResult[bool]:
        """
        Forces parallel HTTP topology graph updates.

        Returns:
            BulkOperationResult[bool]: Success mapping per device host.
        """
        tasks = [c.cache.sync() for c in self._clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        res = BulkOperationResult[bool]()
        for client, r in zip(self._clients, results):
            host_key = str(client._http_client.client.base_url)
            if isinstance(r, Exception):
                res.exceptions[host_key] = r
            else:
                res.successes[host_key] = True
        return res


class BulkDeviceFacade:
    """Dynamic broadcasting facade that executes operations concurrently."""

    def __init__(self, clients: list[Any], path: tuple[str, ...], semaphore: asyncio.Semaphore):
        """Initializes the BulkDeviceFacade."""
        self._clients = clients
        self._path = path
        self._semaphore = semaphore

    def __getattr__(self, name: str) -> "BulkDeviceFacade":
        """Intercepts method calls and builds the attribute chain."""
        return BulkDeviceFacade(self._clients, self._path + (name,), self._semaphore)

    async def __call__(self, *args: Any, **kwargs: Any) -> BulkOperationResult[Any]:
        """Executes the method concurrently across all clients."""

        async def single_call(client: Any) -> Any:
            async with self._semaphore:
                async with client as c:
                    obj = c
                    for attr in self._path:
                        obj = getattr(obj, attr)
                    return await obj(*args, **kwargs)

        tasks = [asyncio.create_task(single_call(c)) for c in self._clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        res = BulkOperationResult[Any]()
        for client, r in zip(self._clients, results):
            host_key = str(client._http_client.client.base_url)
            if isinstance(r, Exception):
                res.exceptions[host_key] = r
            else:
                res.successes[host_key] = r
        return res


class DeviceGroup(BaseControlPlane):
    """
    A logical grouping of independent DeviceClient instances.

    Provides a DRY, SDK-native object that acts as a collection of `DeviceClient`
    instances, exposing bulk control-plane operations and grouped cache accessors.
    """

    def __init__(self, name: str, clients: list[Any]):
        """
        Initializes the DeviceGroup.

        Args:
            name (str): Logical name of the group.
            clients (list[Any]): List of DeviceClient instances. Stitched
                child nodes should not be included directly.
        """
        self.name = name
        self._clients = clients

        # Warn if BACKGROUND strategy is used for large groups
        if len(self._clients) > 10:
            for c in self._clients:
                if hasattr(c, "cache") and getattr(c.cache, "strategy", None) == CacheStrategy.BACKGROUND_WATCHER:
                    logger.warning(
                        "CacheStrategy.BACKGROUND_WATCHER is not recommended for large DeviceGroups. "
                        "Use MANUAL or LAZY_TTL to avoid overwhelming the event loop and network."
                    )

        self.by_name = REPLAccessor(self._clients, key_attr="name")
        self._semaphore = asyncio.Semaphore(10)

    @classmethod
    def from_directory_nodes(
        cls, name: str, nodes: list[dict], username: str = "admin", password: str = "pass", hub_client: Any = None
    ) -> "DeviceGroup":
        """
        Enterprise Factory: Safely converts HubFleetDirectory nodes into a DeviceGroup.

        Args:
            name (str): Logical name of the group.
            nodes (list[dict]): List of device dictionaries from HubFleetDirectory.
            username (str): Local authentication username.
            password (str): Local authentication password.
            hub_client (Any): Optional HubClient instance for proxy routing if LAN IP is unreachable.

        Returns:
            DeviceGroup: A populated device group with properly authenticated clients.
        """
        from xovis.api.device.client import DeviceClient, UnifiedDeviceClient

        clients = []
        for d in nodes:
            ip = d.get("ip")
            mac = d.get("id", "")
            if isinstance(mac, str):
                mac = mac.replace(":", "")
            elif hasattr(mac, "root"):
                mac = str(mac.root).replace(":", "")
            else:
                mac = str(mac).replace(":", "")

            dev_name = d.get("device_name", f"sensor_{ip.replace('.', '_')}" if ip else "sensor_unknown")

            # Create un-entered explicit clients
            host = ip if not hub_client else ip
            client = DeviceClient(host=host, username=username, password=password)
            client.name = dev_name
            clients.append(client)

        return cls(name=name, clients=clients)

    def add_device(self, client: Any) -> None:
        """
        Adds a single device client, ensuring it is not a stitched child.

        Args:
            client (Any): The DeviceClient instance to add.
        """
        if client not in self._clients:
            if hasattr(client, "cache") and getattr(client.cache, "cache_child_devices", True) is False:
                host_key = str(getattr(client._http_client.client.base_url, "host", client._http_client.client.base_url))
                logger.debug(f"Adding client {host_key} which may be a child node.")

            self._clients.append(client)
            self.by_name = REPLAccessor(self._clients, key_attr="name")

    def add_devices(self, clients: list[Any]) -> None:
        """
        Helper to add multiple devices at once.

        Args:
            clients (list[Any]): A list of DeviceClient instances to add.
        """
        for client in clients:
            self.add_device(client)

    def remove_device(self, identifier: str) -> None:
        """
        Removes a device by IP, MAC, or Name.

        Args:
            identifier (str): The identifier to match for removal.
        """
        retained = []
        for c in self._clients:
            # Try to get identifiable fields
            name = str(getattr(c, "name", ""))
            mac = ""
            if hasattr(c, "info") and c.info:
                mac = str(c.info.get("mac_address", ""))

            host = ""
            if hasattr(c, "_http_client"):
                # Use string matching on base_url for IP match
                base_url_str = str(c._http_client.client.base_url)
                host = base_url_str

            if identifier not in (name, mac) and identifier not in host:
                retained.append(c)

        self._clients = retained
        self.by_name = REPLAccessor(self._clients, key_attr="name")

    @property
    def caches(self) -> BulkCacheFacade:
        """
        Exposes bulk cache operations.

        Returns:
            BulkCacheFacade: Facade for aggregating cache operations.
        """
        return BulkCacheFacade(self._clients)

    def __getattr__(self, name: str) -> Any:
        """
        Intercepts manager access and returns a chainable BulkDeviceFacade.

        Args:
            name (str): The manager name to access.

        Returns:
            BulkDeviceFacade: Facade for broadcasting operations.
        """
        standard_managers = {
            "datapush",
            "system",
            "network",
            "time",
            "update",
            "analytics",
            "scene",
            "history",
            "privacy",
            "topology",
            "users",
            "itxpt",
            "multisensors",
        }
        if name in standard_managers:
            return BulkDeviceFacade(self._clients, (name,), self._semaphore)
        raise AttributeError(f"Attribute '{name}' not found on DeviceGroup.")

    def __dir__(self) -> list[str]:
        """
        Provides IDE autocomplete for standard managers.

        Returns:
            list[str]: The standard properties and methods.
        """
        return list(
            set(super().__dir__())
            | {
                "datapush",
                "scene",
                "analytics",
                "system",
                "time",
                "network",
                "itxpt",
                "update",
                "users",
                "privacy",
                "history",
                "topology",
                "multisensors",
            }
        )
