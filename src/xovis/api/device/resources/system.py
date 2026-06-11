"""
Xovis SDK - System Management Resource

Operates within the Control Plane.
Provides the implementation for managing device-level system operations,
including hardware identification, diagnostic log retrieval, configuration
backups, and destructive lifecycle commands. Critical for Autonomous
Fleet Maintenance (Module D).
"""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import ValidationError

from xovis.api.core.exceptions import SDKFirmwareDriftError
from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class SystemManager:
    """
    Manages core system operations, diagnostics, and lifecycle states on a Xovis device.

    This manager acts as the primary interface for hardware-level orchestration,
    enabling agents to pull plaintext logs, manage configuration backups, update
    physical metadata (Name/Group), and execute critical state resets.
    """

    def __init__(
        self,
        http_client: XovisHTTPClient,
        client: Optional["DeviceClient"] = None,
        target_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the SystemManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (Optional[DeviceClient]): The parent DeviceClient instance.
            target_id (Optional[str]): The multisensor target ID, if applicable.
        """
        self._http = http_client
        self._client = client
        self.target_id = target_id
        self._base_path = "/api/v5/device"

    @property
    def models(self) -> Any:
        """
        Returns the strictly validated Pydantic models for the current firmware.

        Returns:
            Any: The collection of auto-generated Pydantic V2 models
                synchronized with the current device firmware.
        """
        return self._client.models if self._client else stable_models

    def _resolve_singlesensor_path(self) -> str:
        """
        Resolves the singlesensor/multisensor status path based on context.

        Returns:
            str: The resolved API path for status and identity operations.
        """
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}"
        return "/api/v5/singlesensor"

    async def get_info(self) -> Any:
        """
        Retrieves static hardware and identity metadata from the sensor.

        Returns:
            DeviceInfo: The sensor's hardware, revisions, and firmware details.
        """
        response = await self._http.get(f"{self._base_path}/info")
        try:
            return self.models.DeviceInfo.model_validate(response.json(), strict=False)
        except ValidationError as e:
            raise SDKFirmwareDriftError(f"System info payload unparsable: {e}")

    async def get_state(self) -> Any:
        """
        Retrieves the real-time device health, temperatures, and uptime.

        Returns:
            DeviceState: The current operational state and thermal metrics.
        """
        response = await self._http.get(f"{self._base_path}/state")
        try:
            # Pydantic V2 model validation
            return self.models.DeviceState1.model_validate(response.json(), strict=False)
        except ValidationError as e:
            raise SDKFirmwareDriftError(f"System state payload unparsable: {e}")
        except AttributeError:
            # Fallback if the dynamic models are not behaving as expected
            return response.json()

    async def get_status(self) -> Any:
        """
        Retrieves the operational status of the sensor (illumination, tilt, etc.).

        Returns:
            SinglesensorStatus: The current operational status.
        """
        response = await self._http.get(f"{self._resolve_singlesensor_path()}/status")
        return self.models.SinglesensorStatus.model_validate(response.json())

    async def get_license(self) -> Any:
        """
        Retrieves the active/expired states of premium features.

        Returns:
            Dict[str, Any]: A mapping of feature IDs to their current license state.
        """
        # Fixed native SDK endpoint for V5 firmwares
        response = await self._http.get("/api/v5/license/features")
        response.raise_for_status()

        # If your LicenseStatus model doesn't match this exact payload yet,
        # return the raw dict for the LLM to parse natively for now.
        return response.json()

    async def get_device_identity(self) -> Any:
        """
        Retrieves the configured logical Name and Group of the physical sensor.

        Returns:
            DeviceId: The logical identifier metadata of the device.
        """
        response = await self._http.get(f"{self._base_path}/id")
        return self.models.DeviceId.model_validate(response.json(), strict=False)

    async def update_device_identity(self, name: str, group: str) -> None:
        """
        Updates the logical Name and Group of the physical sensor.

        Args:
            name (str): The new human-readable name of the sensor.
            group (str): The logical group assignment.
        """
        payload = {"name": name, "group": group}
        await self._http.put(f"{self._resolve_singlesensor_path()}/identity", json=payload)

    async def get_logs(self) -> str:
        """
        Retrieves the raw device user logfile in plaintext.

        Crucial for Autonomous Maintenance agents to parse root-cause
        failures (e.g., token synchronization errors, connection timeouts).

        Returns:
            str: The raw plaintext log stream.
        """
        response = await self._http.get(f"{self._base_path}/log")
        response.raise_for_status()
        return response.text

    async def get_license_details(self) -> Any:
        """
        Retrieves the detailed active, expired, and test states of premium features.

        Returns:
            LicenseStatusDetailed: The comprehensive license status map.
        """
        response = await self._http.get("/api/v5/license/status/details")
        return self.models.LicenseStatusDetailed.model_validate(response.json(), strict=False)

    async def trigger_backup(self) -> None:
        """
        Triggers an asynchronous backup of the sensor configuration.

        This is a non-blocking request. The agent must subsequently poll
        `get_backup_state()` to verify completion before downloading.
        """
        await self._http.post(f"{self._base_path}/backup")

    async def get_backup_state(self) -> Any:
        """
        Retrieves the state of the current configuration backup process.

        Returns:
            DiagBundleState: The current generation state (e.g., IN_PROGRESS, AVAILABLE).
        """
        response = await self._http.get(f"{self._base_path}/backup/state")
        return self.models.DiagBundleState.model_validate(response.json(), strict=False)

    async def download_backup(self) -> bytes:
        """
        Downloads the encrypted backup archive of the sensor configuration.

        Returns:
            bytes: The binary archive payload.
        """
        response = await self._http.get(f"{self._base_path}/backup")
        response.raise_for_status()
        return response.content

    async def restore_backup(self, backup_binary: bytes, ip_handling: str = "check") -> None:
        """
        Restores the sensor configuration from a binary backup file.

        Args:
            backup_binary (bytes): The raw binary archive to restore.
            ip_handling (str): How to handle IP config mismatches. Options:
                'check' (fail if mismatch), 'keep' (retain current IP),
                'overwrite' (apply IP from backup). Defaults to 'check'.
        """
        params = {"ip": ip_handling} if ip_handling else {}
        headers = {"Content-Type": "application/octet-stream"}
        response = await self._http.put(f"{self._base_path}/restore", params=params, content=backup_binary, headers=headers)
        response.raise_for_status()

    async def get_led(self) -> Any:
        """
        Retrieves the current physical LED configuration.

        Returns:
            DeviceLedMode: The current LED mode indicator.
        """
        response = await self._http.get(f"{self._base_path}/led")
        try:
            return self.models.DeviceLedMode.model_validate(response.json(), strict=False)
        except ValidationError as e:
            raise SDKFirmwareDriftError(f"LED configuration payload unparsable: {e}")

    async def update_led(self, led_mode: Any) -> None:
        """
        Updates the physical LED configuration.

        Args:
            led_mode (DeviceLedMode): The new LED configuration payload.
        """
        payload = led_mode.model_dump(by_alias=True, exclude_unset=True, mode="json")
        await self._http.put(f"{self._base_path}/led", json=payload)

    async def reboot(self) -> None:
        """
        Triggers a standard hardware reboot.
        Causes a temporary gap in counting and API accessibility.
        """
        await self._http.post(f"{self._base_path}/reboot")

    async def reboot_rescue(self) -> None:
        """
        CRITICAL: Triggers a reboot into Rescue Mode.
        Halts the standard API and counting logic entirely. Requires human
        intervention or rescue-API firmware flashing to recover.
        """
        await self._http.post(f"{self._base_path}/reboot/rescue")

    async def reset(self) -> None:
        """
        CRITICAL: Triggers a Scene and Data Reset.
        Wipes all geometries, logic configurations, and historical databases.
        Network and User configurations are preserved. Device will reboot.
        """
        await self._http.post(f"{self._base_path}/reset")

    async def hard_reset(self, smk: str) -> None:
        """
        CRITICAL: Triggers a complete Factory Hard Reset.
        Deletes all data, configurations, and network settings.

        Args:
            smk (str): The Sensor Master Key required to authorize the wipe.
        """
        payload = {"smk": smk}
        await self._http.post(f"{self._base_path}/reset/hard", json=payload)

    async def format_flash(self) -> None:
        """
        CRITICAL: Formats the internal flash storage.
        Deletes data, configs, and parts of the firmware. The sensor will
        reboot into rescue mode and require a manual firmware reinstall.
        """
        await self._http.post(f"{self._base_path}/flash/format")
