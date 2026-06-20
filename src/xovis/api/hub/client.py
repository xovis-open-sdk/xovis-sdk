"""
Xovis SDK - HUB Cloud Client

This module resides within the State & Topology Plane, serving as the primary
entry point for fleet orchestration via the Xovis HUB Cloud. It coordinates
OAuth2 authentication, dynamic OpenAPI device tunneling, and concurrent bulk
operations across distributed edge sensors.
"""

import asyncio
from collections.abc import AsyncIterator, Coroutine
from typing import Any, Callable, Optional, TypeVar

import httpx

from xovis.api.core.auth import HubAuth
from xovis.api.core.http import XovisHTTPClient
from xovis.api.device.client import DeviceClient
from xovis.api.device.models import BulkResult
from xovis.api.hub.cache import HubCacheManager
from xovis.api.hub.resources.hub_device import HubDevicesManager
from xovis.api.hub.resources.hub_license import HubLicensesManager

T = TypeVar("T")


class HubClient:
    """
    Asynchronous client for interacting with the Xovis HUB Cloud.

    Manages the complete lifecycle of the Xovis fleet, including automated
    OAuth2 token rotation, client-side state caching, and secure Hub-to-Edge
    tunneling. Acts as the definitive orchestrator for distributed sensor networks.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token: Optional[str] = None,
        base_url: str = "https://api.xovis.cloud",
        token_url: str = "https://login.xovis.cloud/oauth/token",
        tunnel_base_url: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 5,
        fleet_filter: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the HubClient and mounts architectural pillars.

        Args:
            client_id (Optional[str], optional): The OAuth2 Client ID provided by Xovis.
                If not provided, resolves from XOVIS_HUB_CLIENT_ID env var.
            client_secret (Optional[str], optional): The OAuth2 Client Secret provided by Xovis.
                If not provided, resolves from XOVIS_HUB_CLIENT_SECRET env var.
            token (Optional[str], optional): Optional static API token.
            base_url (str, optional): The base URL for the Xovis HUB Cloud API.
                Defaults to "https://api.xovis.cloud".
            token_url (str, optional): The Auth0 token endpoint.
                Defaults to "https://login.xovis.cloud/oauth/token".
            tunnel_base_url (Optional[str], optional): Optional override for the
                device tunnel base URL. If not provided, the `base_url` is used.
            timeout (float, optional): Default timeout for HTTP operations.
                Defaults to 15.0.
            max_retries (int, optional): Maximum retry attempts for resilient
                networking. Defaults to 5.
            fleet_filter (Optional[Dict[str, Any]], optional): Client-side filter
                to restrict the visible fleet scope.
            **kwargs (Any): Additional configuration for the HTTP engine.
        """
        import os

        cid = client_id or os.getenv("XOVIS_HUB_CLIENT_ID")
        csec = client_secret or os.getenv("XOVIS_HUB_CLIENT_SECRET")
        static_token = token or os.getenv("XOVIS_HUB_TOKEN")

        if not static_token and (not cid or not csec):
            raise ValueError(
                "Missing Xovis HUB credentials. Provide token, or client_id/client_secret "
                "or set XOVIS_HUB_TOKEN or XOVIS_HUB_CLIENT_ID/XOVIS_HUB_CLIENT_SECRET environment variables."
            )

        self._auth = HubAuth(client_id=cid, client_secret=csec, token_url=token_url, token=static_token)
        self._tunnel_base_url = tunnel_base_url

        # Extract auto_persist_path if provided
        auto_persist_path = kwargs.pop("auto_persist_path", None)

        self._http_client = XovisHTTPClient(base_url=base_url, auth=self._auth, timeout=timeout, max_retries=max_retries, **kwargs)

        self.cache = HubCacheManager(self._http_client, fleet_filter=fleet_filter, auto_persist_path=auto_persist_path)

        self.devices = HubDevicesManager(self._http_client, cache=self.cache)
        self.licenses = HubLicensesManager(self._http_client, cache=self.cache)

    async def connect_device(self, id_or_name: str) -> DeviceClient:
        """
        Spawns a DeviceClient routed through the Hub's dynamic secure tunnel.

        Enables seamless transition from fleet-level management to specific
        edge sensor configuration. Intercepts OAuth2 tokens to authenticate
        the proxied connection.

        The tunnel URL is dynamically constructed per the OpenAPI specification:
        `{base_url}/devices/{mac_address}/tunnel`. The DeviceClient will then
        append its own paths (e.g., `/api/v5/...`).

        CRITICAL: The returned client MUST be used as an asynchronous context
        manager to prevent connection pooling leaks.

        Args:
            id_or_name (str): The MAC address (ID) or human-readable name of
                the target device.

        Returns:
            DeviceClient: A fully hydrated client instance routed via the HUB.
        """
        # Resolves the human-readable name to a MAC address using the local cache
        mac_address = self.devices._resolve_mac_address(id_or_name)

        # Dynamic OpenAPI routing
        base = self._tunnel_base_url or self._http_client.base_url
        tunnel_url = f"{base}/devices/{mac_address}/tunnel"

        client = DeviceClient(
            host=tunnel_url,
            username="hub_tunnel",
            password="hub_tunnel",
            timeout=60.0,  # Explicitly increased for heavy historical aggregations
            max_retries=self._http_client.max_retries,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
        )

        # Inject Hub authentication for the proxied requests
        client._auth = self._auth
        client._http_client.auth = self._auth
        client._http_client.client.auth = self._auth

        return client

    async def bulk_execute(
        self,
        func: Callable[[DeviceClient], Coroutine[Any, Any, T]],
        fleet_filter: Optional[dict[str, Any]] = None,
    ) -> dict[str, BulkResult[T]]:
        """
        Maps an asynchronous function across the fleet.

        Executes the provided coroutine concurrently across devices in the
        cache using strict fault isolation. Failures on individual devices do
        not interrupt the execution of the remaining fleet.

        Args:
            func (Callable[[DeviceClient], Coroutine[Any, Any, T]]): The async
                configuration function to execute. Receives a connected
                DeviceClient as its primary argument.
            fleet_filter (Optional[Dict[str, Any]]): Dictionary to restrict execution.
                Supported keys: 'macs' (List[str]) to target specific devices.

        Returns:
            Dict[str, BulkResult[T]]: A mapping of MAC addresses to their
                respective execution outcomes.
        """

        async def _execute_single(mac_address: str) -> tuple[str, BulkResult[T]]:
            try:
                async with await self.connect_device(mac_address) as device:
                    result = await func(device)
                    return mac_address, BulkResult[T](success=True, result=result)
            except Exception as e:
                return mac_address, BulkResult[T](success=False, error=str(e))

        # Extract all cached MACs
        macs = [d.id.root if hasattr(d.id, "root") else d.id for d in self.cache._state.devices]

        # Apply specific target filters if provided by an agent
        if fleet_filter and "macs" in fleet_filter:
            target_macs = [m.upper() for m in fleet_filter["macs"]]
            macs = [m for m in macs if m.upper() in target_macs]

        tasks = [_execute_single(mac) for mac in macs]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {mac: res for mac, res in results}

    async def __aiter__(self) -> AsyncIterator[DeviceClient]:
        """
        Enables asynchronous iteration over the cached fleet devices.

        Yields:
            DeviceClient: A connected DeviceClient for each device in the fleet.
        """
        macs = [d.id.root if hasattr(d.id, "root") else d.id for d in self.cache._state.devices]
        for mac in macs:
            async with await self.connect_device(mac) as client:
                yield client

    async def __aenter__(self) -> "HubClient":
        """
        Enables asynchronous context management and triggers initial sync.

        Returns:
            HubClient: The initialized and synchronized client.
        """
        await self._http_client.__aenter__()
        await self.cache.load_from_disk()
        await self.cache.sync()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Ensures graceful teardown of the HTTP connection pool.
        """
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        """
        Manually releases all underlying network resources.
        """
        await self._http_client.aclose()
