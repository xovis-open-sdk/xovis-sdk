"""
Xovis SDK - Device Client

This module resides within the State & Topology Plane, providing the primary
entry point for interacting with Xovis edge sensors. It implements the
`DeviceClient`, a stateful and topology-aware asynchronous manager that
orchestrates authentication, configuration caching, and fleet discovery.
"""

import asyncio
import ipaddress
import re
import signal
import sys
from typing import Any, Optional

from xovis.api.core.auth import DeviceAuth
from xovis.api.core.exceptions import AmbiguousDeviceNameError, EndpointNotFoundError, ForbiddenError, HardwareNotSupportedError, XovisAuthError
from xovis.api.core.http import XovisHTTPClient
from xovis.api.device.resources.analytics import AnalyticsManager
from xovis.api.device.resources.datapush import DataPushManager
from xovis.api.device.resources.history import HistoryManager
from xovis.api.device.resources.images import ImagesManager
from xovis.api.device.resources.itxpt import ITxPTManager

# Import baseline models for typing purposes
from xovis.api.device.resources.network import NetworkManager
from xovis.api.device.resources.privacy import PrivacyManager
from xovis.api.device.resources.scene import SceneManager
from xovis.api.device.resources.system import SystemManager
from xovis.api.device.resources.time_config import TimeManager
from xovis.api.device.resources.update import UpdateManager
from xovis.api.device.resources.users import UsersManager
from xovis.utils.loop import setup_optimal_loop

from .cache import ConfigCacheManager
from .models import CacheStrategy
from .topology import MultisensorsManager, TopologyManager


class SinglesensorContext:
    """
    Isolated context strictly for the physical device lenses.

    Provides access to core resource managers (DataPush, Scene, Analytics)
    bound to the physical sensor hardware. This context is disabled on
    lensless hardware profiles like the Spider NUC.
    """

    def __init__(self, client: Any):
        """
        Initializes the SinglesensorContext.

        Args:
            client (DeviceClient): The parent device client instance.
        """
        self._client = client
        self._datapush = DataPushManager(client)
        self._scene = SceneManager(client)
        self._analytics = AnalyticsManager(client)
        self._history = HistoryManager(client)
        self.update = UpdateManager(client)
        self.images = ImagesManager(client)
        self._privacy = PrivacyManager(client._http_client, client=client)

    @property
    def datapush(self) -> DataPushManager:
        """Accesses the DataPush management manager."""
        if self._client.is_spider:
            raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Access 'datapush' via the 'multisensors' context.")
        return self._datapush

    @property
    def analytics(self) -> AnalyticsManager:
        """Accesses the Analytics management manager."""
        if self._client.is_spider:
            raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Access 'analytics' via the 'multisensors' context.")
        return self._analytics

    @property
    def history(self) -> HistoryManager:
        """Accesses the History management manager."""
        if self._client.is_spider:
            raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Access 'history' via the 'multisensors' context.")
        return self._history

    @property
    def scene(self) -> SceneManager:
        """Accesses the Scene management manager."""
        if self._client.is_spider:
            raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Access 'scene' via the 'multisensors' context.")
        return self._scene

    @property
    def privacy(self) -> PrivacyManager:
        """
        Accesses the Privacy management manager.

        Returns:
            PrivacyManager: Manager for masking and blurring.

        Raises:
            HardwareNotSupportedError: If accessed on a lensless Spider NUC.
        """
        if self._client.is_spider:
            raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Access 'scene' and 'privacy' via the 'multisensors' context.")
        return self._privacy


from xovis.api.device.base import BaseControlPlane


class DeviceClient(BaseControlPlane):
    """
    Stateful & Topology-Aware Asynchronous Client for Xovis environments.

    Orchestrates the lifecycle of a connection to a Xovis sensor, including
    automated background configuration caching, multisensor discovery, and
    graceful resource cleanup.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_ntlm: bool = False,
        timeout: float = 15.0,
        max_retries: int = 5,
        cache_strategy: CacheStrategy = CacheStrategy.MANUAL,
        cache_ttl_seconds: float = 60.0,
        cache_poll_interval: float = 10.0,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the DeviceClient.

        Args:
            host (str): IP address or hostname of the sensor.
            username (str): Authentication username.
            password (str): Authentication password.
            use_ntlm (bool, optional): Whether to use NTLM authentication. Defaults to False.
            timeout (float, optional): Request timeout in seconds. Defaults to 15.0.
            max_retries (int, optional): Max retry attempts for transient failures. Defaults to 5.
            cache_strategy (CacheStrategy, optional): Config sync strategy. Defaults to MANUAL.
            cache_ttl_seconds (float, optional): TTL for cached entries. Defaults to 60.0.
            cache_poll_interval (float, optional): Polling frequency for state hash. Defaults to 10.0.
            **kwargs (Any): Additional keyword arguments passed to the HTTP client.
        """
        setup_optimal_loop()

        base_url = f"http://{host}" if not host.startswith("http") else host

        # Extract SDK-specific kwargs before passing to HTTP client
        auto_persist_path = kwargs.pop("auto_persist_path", None)
        persistence_dir = kwargs.pop("persistence_dir", None)
        cache_child_devices = kwargs.pop("cache_child_devices", False)

        self._auth = DeviceAuth(username=username, password=password, use_ntlm=use_ntlm)
        self._http_client = XovisHTTPClient(
            base_url=base_url,
            auth=self._auth,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

        self.cache = ConfigCacheManager(
            http_client=self._http_client,
            strategy=cache_strategy,
            ttl_seconds=cache_ttl_seconds,
            poll_interval=cache_poll_interval,
            auto_persist_path=auto_persist_path,
            persistence_dir=persistence_dir,
            cache_child_devices=cache_child_devices,
        )
        self.cache._parent_client = self

        self._singlesensor = SinglesensorContext(self)
        self._device_info = {}
        self.fw_version = "unknown"

        # Cached resource managers
        self._network = None
        self._system = None
        self._time = None
        self._itxpt = None
        self._update = None
        self._topology = None
        self._multisensors = None
        self._users = None
        self._privacy_manager = None

        # Dynamically linked models facade
        from xovis.models import device_auto

        self.models = device_auto

        self._capability_cache: dict[str, bool] = {}

    async def _probe_capability(self, key: str, endpoint: str) -> bool:
        """
        Lazy asynchronous probe for hardware capabilities.

        Args:
            key (str): The unique capability identifier.
            endpoint (str): The API endpoint to probe.

        Returns:
            bool: True if the capability is supported and authorized.
        """
        if key in self._capability_cache:
            return self._capability_cache[key]

        try:
            # FIX: Use configured max_retries
            resp = await self._http_client.get(endpoint, max_retries=self._http_client.max_retries)
            is_supported = resp.status_code == 200
        except EndpointNotFoundError as e:
            # Xovis sensors return HTML 403 (mapped to EndpointNotFoundError) when features are missing/restricted.
            # We interpret this as a definitive "False" for the capability.
            import logging

            logging.getLogger(__name__).debug(f"Capability '{key}' restricted or not found at {endpoint}: {e}")
            is_supported = False
        except ForbiddenError as e:
            # Authorization failure (not HTML 403)
            import logging

            logging.getLogger(__name__).debug(f"Capability '{key}' forbidden at {endpoint}: {e}")
            is_supported = False
        except XovisAuthError as e:
            # Standard 401 Auth error should still be False for capability
            import logging

            logging.getLogger(__name__).debug(f"Capability '{key}' auth failed at {endpoint}: {e}")
            is_supported = False
        except Exception as e:
            # FIX: Stop silently swallowing errors! Log the failure for diagnostics.
            import logging

            logging.getLogger(__name__).debug(f"Capability probe for '{key}' failed at {endpoint}: {e}")
            is_supported = False

        self._capability_cache[key] = is_supported
        return is_supported

    async def has_capability(self, endpoint: str) -> bool:
        """
        Ad-hoc probe for a specific endpoint capability.
        """
        try:
            # FIX: Use configured max_retries
            resp = await self._http_client.get(endpoint, max_retries=self._http_client.max_retries)
            return resp.status_code == 200
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"Ad-hoc capability probe failed at {endpoint}: {e}")
            return False

    async def get_privacy_state(self) -> str:
        """
        Retrieves the current privacy mode of the sensor.

        Returns:
            str: The privacy mode identifier (e.g., "0", "1", "2", "3", "4").
        """
        try:
            privacy_mode = await self.privacy.get_privacy_mode()
            # Handle both object-based and raw dictionary responses
            if hasattr(privacy_mode, "mode"):
                return str(privacy_mode.mode)
            elif isinstance(privacy_mode, dict) and "mode" in privacy_mode:
                return str(privacy_mode["mode"])
            return str(privacy_mode)
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"Failed to retrieve privacy state: {e}")
            return "unknown"

    @property
    async def has_wifi(self) -> bool:
        """
        Checks if the hardware supports WiFi/BT monitoring.

        Returns:
            bool: True if RF privacy endpoints are accessible.
        """
        return await self._probe_capability("wifi", "/api/v5/rf/privacy")

    @property
    async def has_itxpt(self) -> bool:
        """
        Checks if the hardware supports ITxPT (Public Transport).

        Returns:
            bool: True if ITxPT state endpoints are accessible.
        """
        return await self._probe_capability("itxpt", "/api/v5/itxpt/state")

    @property
    async def has_analytics(self) -> bool:
        """
        Checks if the sensor supports and is authorized for analytics.

        Returns:
            bool: True if analytics logics endpoints are accessible.
        """
        return await self._probe_capability("analytics", "/api/v5/singlesensor/analysis/logics")

    async def _probe_license(self, feature_id: int) -> bool:
        """
        Probes the device for a specific license feature by ID.

        Args:
            feature_id (int): The unique Xovis feature identifier.

        Returns:
            bool: True if the license is active (ENABLED or TEST_ENABLED).
        """
        cache_key = f"license_{feature_id}"
        if cache_key in self._capability_cache:
            return self._capability_cache[cache_key]

        try:
            # We use the system manager's license details endpoint
            details = await self.system.get_license_details()
            if not details or not details.licenses:
                is_active = False
            else:
                # Search for the feature ID and check state
                is_active = any(lic.id == feature_id and lic.state.value in ("ENABLED", "TEST_ENABLED") for lic in details.licenses)
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"License probe for ID {feature_id} failed: {e}")
            is_active = False

        self._capability_cache[cache_key] = is_active
        return is_active

    @property
    def has_object_detection(self) -> Any:
        """
        Checks for core Object Detection license (PIVID=116).

        Returns:
            Awaitable[bool]: True if the license is active.
        """
        return self._probe_license(116)

    @property
    def has_pram_detection(self) -> Any:
        """
        Checks for Pram extension license (PIGES=112).

        Returns:
            Awaitable[bool]: True if the license is active.
        """
        return self._probe_license(112)

    @property
    def has_wheelchair_detection(self) -> Any:
        """
        Checks for Wheelchair extension license (PISTE=113).

        Returns:
            Awaitable[bool]: True if the license is active.
        """
        return self._probe_license(113)

    @property
    def has_bicycle_detection(self) -> Any:
        """
        Checks for Bicycle extension license (PIBCL=114).

        Returns:
            Awaitable[bool]: True if the license is active.
        """
        return self._probe_license(114)

    @property
    def has_people_attributes(self) -> Any:
        """
        Checks for People Attributes license (PIFMD=117).

        Returns:
            Awaitable[bool]: True if the license is active.
        """
        return self._probe_license(117)

    @property
    def info(self) -> Optional[dict[str, Any]]:
        """
        Retrieves raw device information fetched during connection.

        Returns:
            Optional[Dict[str, Any]]: The hardware profile metadata.
        """
        return self._device_info

    @property
    def is_spider(self) -> bool:
        """
        Checks if the hardware is a lensless Spider NUC.

        Returns:
            bool: True if the device type contains 'Spider' or 'SPIDER',
                or if the product code indicates a Spider unit.
        """
        if not self._device_info:
            return False
        device_type = self._device_info.get("type", "").upper()
        prod_code = self._device_info.get("prod_code", "").upper()
        return "SPIDER" in device_type or "SPI-PU1" in prod_code or "SPI-PU2" in prod_code

    @property
    def active_contexts(self) -> list:
        """
        Returns a flat, iterable list of valid hardware-aware contexts.

        For standard sensors (PC/PF-series): Returns [singlesensor] + multisensors.
        For Spiders: Returns only the multisensor contexts.

        Returns:
            list: A list containing SinglesensorContext and/or MultisensorContext instances.
        """
        contexts = []
        if not self.is_spider:
            contexts.append(self.singlesensor)

        # Add all discovered multisensor contexts
        contexts.extend(list(self.multisensors._contexts))
        return contexts

    @property
    def singlesensor(self) -> SinglesensorContext:
        """
        Accessor for the physical lens context.

        Returns:
            SinglesensorContext: The physical hardware management context.
        """
        return self._singlesensor

    @property
    def datapush(self) -> DataPushManager:
        """
        Direct accessor for DataPush management (shortcut to singlesensor.datapush).

        Returns:
            DataPushManager: The DataPush manager for the physical device.

        Raises:
            HardwareNotSupportedError: If accessed on a lensless Spider NUC.
        """
        return self.singlesensor.datapush

    @property
    def analytics(self) -> AnalyticsManager:
        """
        Direct accessor for Analytics management (shortcut to singlesensor.analytics).

        Returns:
            AnalyticsManager: The Analytics manager for the physical device.

        Raises:
            HardwareNotSupportedError: If accessed on a lensless Spider NUC.
        """
        return self.singlesensor.analytics

    @property
    def scene(self) -> SceneManager:
        """
        Direct accessor for Scene management (shortcut to singlesensor.scene).

        Returns:
            SceneManager: The Scene manager for the physical device.

        Raises:
            HardwareNotSupportedError: If accessed on a lensless Spider NUC.
        """
        return self.singlesensor.scene

    @property
    def history(self) -> HistoryManager:
        """
        Direct accessor for History management (shortcut to singlesensor.history).

        Returns:
            HistoryManager: The History manager for the physical device.

        Raises:
            HardwareNotSupportedError: If accessed on a lensless Spider NUC.
        """
        return self.singlesensor.history

    @property
    def network(self) -> NetworkManager:
        """
        Accesses the Network configuration manager.

        Returns:
            NetworkManager: Manager for IP, DNS, and bridge settings.
        """
        if self._network is None:
            self._network = NetworkManager(self._http_client, client=self)
        return self._network

    @property
    def system(self) -> SystemManager:
        """
        Accesses the System management manager.

        Returns:
            SystemManager: Manager for reboot, reset, and license operations.
        """
        if self._system is None:
            self._system = SystemManager(self._http_client, client=self)
        return self._system

    @property
    def time(self) -> TimeManager:
        """
        Accesses the Time configuration manager.

        Returns:
            TimeManager: Manager for NTP and timezone settings.
        """
        if self._time is None:
            self._time = TimeManager(self._http_client, client=self)
        return self._time

    @property
    def itxpt(self) -> ITxPTManager:
        """
        Accesses the ITxPT management manager.

        Returns:
            ITxPTManager: Manager for public transport protocols.
        """
        if self._itxpt is None:
            self._itxpt = ITxPTManager(self._http_client, client=self)
        return self._itxpt

    @property
    def update(self) -> UpdateManager:
        """
        Accesses the Firmware Update manager.

        Returns:
            UpdateManager: Manager for OTA and local binary flashing.
        """
        if self._update is None:
            self._update = UpdateManager(self)
        return self._update

    @property
    def topology(self) -> TopologyManager:
        """
        Accesses the Topology and Graphing manager.

        Returns:
            TopologyManager: Manager for Multisensor node discovery.
        """
        if self._topology is None:
            self._topology = TopologyManager(self._http_client, parent_client=self)
        return self._topology

    @property
    def multisensors(self) -> MultisensorsManager:
        """
        Accesses the Multisensor cluster manager.

        Returns:
            MultisensorsManager: Manager for virtual stitched environments (Multisensors).
        """
        if self._multisensors is None:
            self._multisensors = MultisensorsManager(self)
        return self._multisensors

    @property
    def users(self) -> UsersManager:
        """
        Accesses the User management manager.

        Returns:
            UsersManager: Manager for local sensor accounts.
        """
        if self._users is None:
            self._users = UsersManager(self._http_client, client=self)
        return self._users

    @property
    def privacy(self) -> PrivacyManager:
        """
        Accesses the Privacy configuration manager.

        Returns:
            PrivacyManager: Manager for masking and blurring settings.
        """
        if self._privacy_manager is None:
            self._privacy_manager = PrivacyManager(self._http_client, client=self)
        return self._privacy_manager

    async def __aenter__(self) -> "DeviceClient":
        """
        Enters the asynchronous context and initializes background engines.

        Establishes connection pools, fetches hardware profiles, hydrates
        multisensor contexts, and starts the configuration cache watcher.

        Returns:
            DeviceClient: The active client instance.
        """
        self._setup_signal_handlers()
        await self._http_client.__aenter__()

        # Aggressive Hardware Probing
        try:
            resp = await self._http_client.get("/api/v5/device/info")
            self._device_info = resp.json()
            self.fw_version = self._device_info.get("fw_version", "unknown") if self._device_info else "unknown"
        except Exception:
            self._device_info = {}
            self.fw_version = "unknown"

        # Capability Probing
        self._capability_cache["advanced_zones"] = "5.9.2" in self.fw_version

        # Model Versioning Selection
        from xovis.models import device_auto

        self.models = device_auto

        if "5.9.2" in self.fw_version:
            self.models = self.models.v5_9_2_models
        else:
            self.models = self.models.stable_models

        # Sync multisensors and start cache watcher
        await asyncio.gather(self.multisensors.sync(), self.cache.start(), return_exceptions=True)

        # Ensure we try to load from disk
        await self.cache.load_from_disk()

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Gracefully shuts down background engines and releases connections.

        Args:
            exc_type (Any): The exception type if an error occurred.
            exc_val (Any): The exception value.
            exc_tb (Any): The traceback object.
        """
        await self.cache.stop()
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        """
        Manual graceful shutdown fallback.
        """
        await self.cache.stop()
        await self._http_client.aclose()

    def _setup_signal_handlers(self) -> None:
        """
        Registers signal handlers for graceful shutdown on POSIX systems.
        """
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.aclose()))


class UnifiedDeviceClient:
    """
    Enterprise-grade hybrid connection router for Xovis devices.

    This class provides a hybrid routing strategy across the control and state planes.
    It supports three connection pathways: MAC-First (resolving MAC addresses with local IP
    handshake and Cloud HUB fallback), IP-First (local connection with HUB proxy fallback),
    and Named Resolution (dynamic name lookups with AmbiguousDeviceNameError handling).

    Attributes:
        mac_address (Optional[str]): Target MAC address.
        host (Optional[str]): Target IP address or hostname.
        name (Optional[str]): Target device name.
        hub_client (Optional[Any]): HubClient instance for Cloud proxy fallback.
        username (str): Local authentication username.
        password (str): Local authentication password.
        kwargs (Any): Additional options passed to DeviceClient.
    """

    def __init__(
        self,
        identifier: Optional[str] = None,
        mac_address: Optional[str] = None,
        host: Optional[str] = None,
        name: Optional[str] = None,
        hub_client: Optional[Any] = None,
        username: str = "admin",
        password: str = "pass",
        **kwargs: Any,
    ) -> None:
        """
        Initializes the UnifiedDeviceClient.

        Args:
            identifier (Optional[str]): Optional single positional identifier (MAC, IP, or Name).
            mac_address (Optional[str]): Target MAC address.
            host (Optional[str]): Target IP address.
            name (Optional[str]): Target device name.
            hub_client (Optional[Any]): Optional HubClient instance.
            username (str): Username for LAN authentication.
            password (str): Password for LAN authentication.
            **kwargs (Any): Extra connection options.
        """
        self.mac_address = mac_address
        self.host = host
        self.name = name
        self.hub_client = hub_client
        self.username = username
        self.password = password
        self.kwargs = kwargs
        self._client: Optional[DeviceClient] = None

        if identifier:
            is_mac = bool(re.match(r"^([0-9A-Fa-f]{2}[:.-]){5}([0-9A-Fa-f]{2})$", identifier))
            is_ip = False
            try:
                ipaddress.ip_address(identifier)
                is_ip = True
            except ValueError:
                pass

            if is_mac:
                self.mac_address = identifier
            elif is_ip:
                self.host = identifier
            else:
                self.name = identifier

    async def __aenter__(self) -> DeviceClient:
        """
        Establishes connection to the device using the optimal route.

        Returns:
            DeviceClient: An active, authenticated device client instance.

        Raises:
            AmbiguousDeviceNameError: If multiple devices share the same name.
            ConnectionError: If all connection attempts and fallbacks fail.
        """
        resolved_mac = self.mac_address
        resolved_host = self.host

        if self.name:
            if not self.hub_client:
                raise ConnectionError("Cannot resolve device name without a HubClient.")
            devices = getattr(self.hub_client.cache._state, "devices", [])
            matches = [d for d in devices if getattr(d, "device_name", None) == self.name]
            if not matches:
                raise ConnectionError(f"Device with name '{self.name}' not found in Hub cache.")
            if len(matches) > 1:
                macs = []
                for d in matches:
                    d_id = getattr(d, "id", None)
                    d_mac = (d_id.root if hasattr(d_id, "root") else d_id) if d_id else "unknown"
                    macs.append(str(d_mac))
                raise AmbiguousDeviceNameError(f"Multiple devices found with name '{self.name}': {', '.join(macs)}")
            matched_dev = matches[0]
            d_id = getattr(matched_dev, "id", None)
            resolved_mac = (d_id.root if hasattr(d_id, "root") else d_id) if d_id else None

        # Path 2: Explicit IP Address is available
        if resolved_host:
            probe_kwargs = self.kwargs.copy()
            probe_kwargs["timeout"] = 2.0
            probe_client = DeviceClient(
                host=resolved_host,
                username=self.username,
                password=self.password,
                **probe_kwargs,
            )
            try:
                async with probe_client:
                    pass
                self._client = DeviceClient(
                    host=resolved_host,
                    username=self.username,
                    password=self.password,
                    **self.kwargs,
                )
                await self._client.__aenter__()
                return self._client
            except Exception:
                pass

        # If IP failed or was not provided, but we don't have a MAC yet
        if not resolved_mac and resolved_host:
            # Cross-Reference for Hub Routing (Fallback)
            if self.hub_client:
                for d in getattr(self.hub_client.cache._state, "devices", []):
                    if getattr(d, "ip", None) == resolved_host:
                        d_id = getattr(d, "id", None)
                        resolved_mac = (d_id.root if hasattr(d_id, "root") else d_id) if d_id else None
                        break

            if not resolved_mac:
                raise ValueError(
                    f"IP {resolved_host} is unreachable on local LAN and cannot be safely routed via Hub without a matching cache entry. Please provide a MAC address."
                )

        # Path 1: Target is a MAC Address (or was resolved to a MAC)
        if resolved_mac:
            from xovis.api.device.network_discovery import NetworkDiscoveryService

            local_ip = await NetworkDiscoveryService.resolve_mac_to_ip(resolved_mac)

            if local_ip and local_ip != resolved_host:
                probe_kwargs = self.kwargs.copy()
                probe_kwargs["timeout"] = 2.0
                probe_client = DeviceClient(
                    host=local_ip,
                    username=self.username,
                    password=self.password,
                    **probe_kwargs,
                )
                try:
                    async with probe_client:
                        pass
                    self._client = DeviceClient(
                        host=local_ip,
                        username=self.username,
                        password=self.password,
                        **self.kwargs,
                    )
                    await self._client.__aenter__()
                    return self._client
                except Exception:
                    pass

            if self.hub_client:
                try:
                    self._client = await self.hub_client.connect_device(resolved_mac)
                    await self._client.__aenter__()
                    return self._client
                except Exception as e:
                    raise ConnectionError(f"Could not connect to device {resolved_mac} via LAN or via Cloud Hub Tunnel: {e}") from e

        desc = resolved_mac or resolved_host or self.name or "unknown"
        raise ConnectionError(f"Device {desc} offline/unreachable on LAN and no HubClient/MAC is available for fallback.")

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Gracefully releases the connected device client resources.

        Args:
            exc_type (Any): The exception type if an error occurred.
            exc_val (Any): The exception value.
            exc_tb (Any): The traceback object.
        """
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
