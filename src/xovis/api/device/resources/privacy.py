"""
Xovis SDK - Privacy Management Resource

Provides the implementation for managing logical privacy modes and RF-based
(Wi-Fi/Bluetooth) monitoring configurations on local edge sensors.
Operates within the Control Plane.
"""

from typing import TYPE_CHECKING, Any, Optional

from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class PrivacyManager:
    """
    Manages privacy modes and RF monitoring settings on a Xovis device.

    This manager provides control over the sensor's privacy levels (e.g., blurring,
    counting only) and the anonymization of detected Wi-Fi/Bluetooth devices.
    """

    def __init__(
        self,
        http_client: XovisHTTPClient,
        client: "DeviceClient" = None,
        target_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the PrivacyManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (DeviceClient): The parent DeviceClient instance.
            target_id (Optional[str]): The multisensor target ID, if applicable.
        """
        self._http = http_client
        self._client = client
        self.target_id = target_id
        self._base_path = "/api/v5/privacy"

    @property
    def models(self):
        """Returns the appropriate Pydantic models for the current device firmware."""
        return self._client.models if self._client else stable_models

    def _resolve_mode_path(self) -> str:
        """Resolves the base API path for privacy modes."""
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}/settings/privacy"
        return "/api/v5/privacy"

    def _resolve_rf_path(self) -> str:
        """Resolves the base API path for RF privacy."""
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}/settings/rf/privacy"
        return "/api/v5/rf/privacy"

    # --- Privacy Mode ---
    async def get_privacy_mode(self) -> Any:
        """
        Retrieves the current logical privacy mode.

        Returns:
            PrivacyMode: The current privacy mode settings.
        """
        path = f"{self._resolve_mode_path()}/mode" if not self.target_id else self._resolve_mode_path()
        response = await self._http.get(path)
        return self.models.PrivacyMode.model_validate(response.json())

    async def update_privacy_mode(self, mode: Any) -> Any:
        """
        Updates the sensor's privacy mode.

        Args:
            mode (PrivacyMode): The new privacy mode configuration.

        Returns:
            PrivacyMode: The updated privacy mode settings.
        """
        payload = mode.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._resolve_mode_path()}/mode", json=payload)
        return self.models.PrivacyMode.model_validate(response.json())

    async def reset_privacy_mode(self) -> None:
        """Resets the privacy mode to factory defaults."""
        await self._http.delete(f"{self._base_path}/mode")

    # --- RF Privacy Settings ---
    async def get_rf_privacy(self) -> Any:
        """
        Retrieves the current RF privacy (hashing/anonymization) configuration.

        Returns:
            PrivacySettings: The current RF privacy settings.
        """
        response = await self._http.get("/api/v5/rf/privacy")
        return self.models.PrivacySettings.model_validate(response.json())

    async def update_rf_privacy(self, settings: Any) -> Any:
        """
        Updates the RF privacy configuration.

        Args:
            settings (PrivacySettings): The new RF privacy settings.

        Returns:
            PrivacySettings: The updated RF privacy settings.
        """
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put("/api/v5/rf/privacy", json=payload)
        return self.models.PrivacySettings.model_validate(response.json())

    async def reset_rf_privacy(self) -> Any:
        """
        Resets the RF privacy configuration to factory defaults.

        Returns:
            PrivacySettings: The default RF privacy settings.
        """
        response = await self._http.delete("/api/v5/rf/privacy")
        return self.models.PrivacySettings.model_validate(response.json())

    async def get_rf_salt(self) -> Any:
        """
        Retrieves the current hashing salt used for RF anonymization.

        Returns:
            PrivacySaltSettings: The current hashing salt.
        """
        response = await self._http.get("/api/v5/rf/privacy/salt")
        return self.models.PrivacySaltSettings.model_validate(response.json())

    async def update_rf_salt(self, settings: Any) -> Any:
        """
        Updates the hashing salt for RF anonymization.

        Args:
            settings (PrivacySaltSettings): The new hashing salt.

        Returns:
            PrivacySaltSettings: The updated hashing salt.
        """
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put("/api/v5/rf/privacy/salt", json=payload)
        return self.models.PrivacySaltSettings.model_validate(response.json())

    async def reset_rf_salt(self) -> Any:
        """
        Resets the RF salt, triggering the generation of a new random salt.

        Returns:
            PrivacySaltSettings: The newly generated salt settings.
        """
        response = await self._http.delete("/api/v5/rf/privacy/salt")
        return self.models.PrivacySaltSettings.model_validate(response.json())

    # --- Bluetooth Settings ---
    async def get_bluetooth(self) -> Any:
        """
        Retrieves the current Bluetooth monitoring configuration.

        Returns:
            BluetoothSettings: The current Bluetooth settings.
        """
        response = await self._http.get("/api/v5/rf/bluetooth")
        return self.models.BluetoothSettings.model_validate(response.json())

    async def update_bluetooth(self, settings: Any) -> Any:
        """
        Updates the Bluetooth monitoring configuration.

        Args:
            settings (BluetoothSettings): The new Bluetooth configuration.

        Returns:
            BluetoothSettings: The updated Bluetooth settings.
        """
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put("/api/v5/rf/bluetooth", json=payload)
        return self.models.BluetoothSettings.model_validate(response.json())

    async def reset_bluetooth(self) -> Any:
        """
        Resets the Bluetooth monitoring configuration to factory defaults.

        Returns:
            BluetoothSettings: The default Bluetooth settings.
        """
        response = await self._http.delete("/api/v5/rf/bluetooth")
        return self.models.BluetoothSettings.model_validate(response.json())

    # --- WiFi Settings ---
    async def get_wifi(self) -> Any:
        """
        Retrieves the current Wi-Fi monitoring configuration.

        Returns:
            WifiSettings: The current Wi-Fi settings.
        """
        response = await self._http.get("/api/v5/rf/wifi")
        return self.models.WifiSettings.model_validate(response.json())

    async def update_wifi(self, settings: Any) -> Any:
        """
        Updates the Wi-Fi monitoring configuration.

        Args:
            settings (WifiSettings): The new Wi-Fi configuration.

        Returns:
            WifiSettings: The updated Wi-Fi settings.
        """
        payload = settings.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put("/api/v5/rf/wifi", json=payload)
        return self.models.WifiSettings.model_validate(response.json())

    async def reset_wifi(self) -> Any:
        """
        Resets the Wi-Fi monitoring configuration to factory defaults.

        Returns:
            WifiSettings: The default Wi-Fi settings.
        """
        response = await self._http.delete("/api/v5/rf/wifi")
        return self.models.WifiSettings.model_validate(response.json())

    # --- Detected Devices ---
    async def get_devices(self) -> Any:
        """
        Retrieves the list of devices detected in the last 5 seconds.

        Returns:
            DeviceIdList: A list of detected device identifiers.
        """
        response = await self._http.get("/api/v5/rf/devices")
        return self.models.DeviceIdList.model_validate(response.json())

    async def get_devices_summary(self) -> str:
        """
        Retrieves a human-readable summary of devices detected in the last 5 seconds.

        Returns:
            str: A formatted list of detected devices.
        """
        response = await self._http.get("/api/v5/rf/devices/summary")
        return response.text
