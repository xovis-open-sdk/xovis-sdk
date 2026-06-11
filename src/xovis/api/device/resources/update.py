"""
Xovis SDK - Firmware Update Resource

Operates within the Control Plane.
Provides comprehensive implementation for managing the firmware update
lifecycle on local edge sensors. This includes OTA (Over-The-Air) cloud
downloads, local binary flashing, installation scheduling, and autonomous
update diagnostics.
"""

from typing import TYPE_CHECKING, Any, Optional

from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class UpdateManager:
    """
    Manages firmware update operations, schedulers, and diagnostics on a Xovis device.

    This manager orchestrates the entire firmware maintenance lifecycle. It allows
    agents to query cloud availability, stream raw firmware binaries, schedule
    off-hours installations, and parse plaintext installation logs for autonomous
    failure remediation.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the UpdateManager.

        Args:
            client (DeviceClient): The parent device client instance providing
                authenticated HTTPX connection pooling.
            target_id (Optional[str]): The multisensor target ID, if applicable.
        """
        self._client = client
        self._http = client._http_client
        self.target_id = target_id
        self._base_path = "/api/v5/updates"

    @property
    def models(self):
        """Returns the strictly validated Pydantic models for the current firmware."""
        return self._client.models if self._client else stable_models

    def _resolve_path(self) -> str:
        """Resolves the base API path for updates."""
        if self.target_id:
            # Note: For multisensors, update status is under stitcher sensors
            return f"/api/v5/multisensors/{self.target_id}/stitcher/sensors/update"
        return "/api/v5/updates"

    async def get_info(self) -> Any:
        """
        Retrieves static minimal update information.

        Returns:
            UpdateInfo: The minimal software version and current version data.
        """
        response = await self._http.get(f"{self._resolve_path()}/info")
        return self.models.UpdateInfo.model_validate(response.json())

    async def get_state(self) -> Any:
        """
        Retrieves the real-time installation and execution state of the update engine.

        Returns:
            UpdateState: Current update state (e.g., OK, INSTALLING, REBOOTING).
        """
        response = await self._http.get(f"{self._resolve_path()}/state")
        return self.models.UpdateState.model_validate(response.json())

    async def get_history(self, include_fails: bool = True) -> Any:
        """
        Retrieves the chronological history of firmware installations.

        Args:
            include_fails (bool): Whether to include failed installation attempts
                in the diagnostic ledger. Defaults to True.

        Returns:
            UpdateHistory: Validated Pydantic model containing the installation ledger.
        """
        params = {"include_fails": "true" if include_fails else "false"}
        response = await self._http.get(f"{self._resolve_path()}/history", params=params)
        return self.models.UpdateHistory.model_validate(response.json())

    async def get_log(self, offset: int = 0) -> str:
        """
        Retrieves the raw plaintext installation log.

        Crucial for autonomous agents to parse why an installation failed
        (e.g., hardware incompatibility or checksum errors).

        Args:
            offset (int): Number of bytes to skip, allowing for polled streaming.

        Returns:
            str: The raw plaintext log output.
        """
        params = {"offset": offset}
        response = await self._http.get(f"{self._resolve_path()}/log", params=params)
        response.raise_for_status()
        return response.text

    async def get_packages(self) -> Any:
        """
        Retrieves the list of firmware packages currently stored on the sensor's flash.

        Returns:
            UpdatePackages: A list of version identifiers currently cached.
        """
        response = await self._http.get(self._resolve_path())
        return self.models.UpdatePackages.model_validate(response.json())

    async def delete_all_packages(self, force: bool = False) -> None:
        """
        Deletes all firmware packages cached on the sensor's internal storage.

        Args:
            force (bool): If True, also deletes any pending scheduled updates.
        """
        params = {"force": "true" if force else "false"}
        await self._http.delete(self._resolve_path(), params=params)

    async def delete_package(self, version: str, force: bool = False) -> None:
        """
        Deletes a specific firmware package from the sensor's storage.

        Args:
            version (str): The exact version identifier of the package.
            force (bool): If True, also deletes if it is currently scheduled.
        """
        params = {"force": "true" if force else "false"}
        await self._http.delete(f"{self._resolve_path()}/{version}", params=params)

    async def upload_firmware(self, file_path: str) -> Any:
        """
        Uploads a firmware update package (.xup) to the sensor's flash memory.

        Bypasses multipart/form-data to stream the raw binary directly,
        satisfying the strict application/octet-stream OpenAPI requirement.

        Args:
            file_path (str): The local filesystem path to the .xup binary.

        Returns:
            UpdateVersion: The parsed version identifier of the uploaded package.
        """
        headers = {"Content-Type": "application/octet-stream"}
        with open(file_path, "rb") as f:
            response = await self._http.post(self._resolve_path(), content=f, headers=headers)
        return self.models.UpdateVersion.model_validate(response.json())

    async def install_package(self, version: str, force: bool = False) -> None:
        """
        Triggers the installation of a firmware package already cached on the sensor.

        Args:
            version (str): The exact version identifier to install.
            force (bool): CRITICAL: If True, forces the installation even if it
                results in a configuration-breaking downgrade.
        """
        params = {"force": "true" if force else "false"}
        await self._http.post(f"{self._resolve_path()}/{version}/install", params=params)

    async def upload_and_install(self, file_path: str, force: bool = False) -> Any:
        """
        Simultaneously datapush and executes a firmware binary installation.

        Args:
            file_path (str): The local filesystem path to the .xup binary.
            force (bool): CRITICAL: If True, forces the installation.

        Returns:
            UpdateVersion: The parsed version identifier of the installed package.
        """
        headers = {"Content-Type": "application/octet-stream"}
        params = {"force": "true" if force else "false"}
        with open(file_path, "rb") as f:
            response = await self._http.post(f"{self._resolve_path()}/install", content=f, headers=headers, params=params)
        return self.models.UpdateVersion.model_validate(response.json())

    async def get_schedule(self) -> Any:
        """
        Retrieves the current automated firmware installation schedule.

        Returns:
            UpdateSchedule: The configured execution time and target version.
        """
        response = await self._http.get(f"{self._resolve_path()}/schedule")
        return self.models.UpdateSchedule.model_validate(response.json())

    async def set_schedule(self, schedule: Any) -> Any:
        """
        Configures an automated future firmware installation.

        Args:
            schedule (UpdateSchedule): The validated Pydantic schedule payload
                containing the target version and XovisTime.

        Returns:
            UpdateSchedule: The confirmed active schedule.
        """
        # Pydantic V2 mode="json" ensures XovisTime is serialized to an integer or
        # compliant ISO string as per the model's configuration.
        payload = schedule.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._resolve_path()}/schedule", json=payload)
        return self.models.UpdateSchedule.model_validate(response.json())

    async def delete_schedule(self) -> None:
        """Cancels any pending automated firmware installation."""
        await self._http.delete(f"{self._resolve_path()}/schedule")

    async def get_config(self) -> Any:
        """
        Retrieves the automated cloud download configuration.

        Returns:
            DownloadConfig: The current automation toggles for minor updates.
        """
        response = await self._http.get(f"{self._resolve_path()}/config")
        return self.models.DownloadConfig.model_validate(response.json())

    async def set_config(self, config: Any) -> Any:
        """
        Modifies the automated cloud download configuration.

        Args:
            config (DownloadConfig): The updated Pydantic configuration model.

        Returns:
            DownloadConfig: The successfully applied configuration.
        """
        payload = config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.put(f"{self._resolve_path()}/config", json=payload)
        return self.models.DownloadConfig.model_validate(response.json())

    async def delete_config(self) -> None:
        """Resets the automated cloud download configuration to factory defaults."""
        await self._http.delete(f"{self._resolve_path()}/config")

    async def get_available_updates(self) -> Any:
        """
        Queries the Xovis Cloud for applicable firmware upgrades.

        Returns:
            UpdatesAvailable: List of compatible firmware metadata.
        """
        response = await self._http.get(f"{self._resolve_path()}/available")
        return self.models.UpdatesAvailable.model_validate(response.json())

    async def refresh_available_updates(self) -> None:
        """Forces the sensor to immediately re-poll the Xovis Cloud for upgrades."""
        await self._http.post(f"{self._resolve_path()}/available/refresh")

    async def get_download_state(self) -> Any:
        """
        Retrieves the real-time progression of an active cloud firmware download.

        Returns:
            DownloadState: The current percentage and error states of the download.
        """
        response = await self._http.get(f"{self._resolve_path()}/download/state")
        return self.models.DownloadState.model_validate(response.json())

    async def start_cloud_download(self, version: str) -> None:
        """
        Commands the sensor to begin downloading a specific firmware version
        from the Xovis Cloud.

        Args:
            version (str): The exact version string to fetch.
        """
        await self._http.post(f"{self._resolve_path()}/download/{version}")

    async def cancel_cloud_download(self) -> None:
        """Aborts any currently active firmware download from the Xovis Cloud."""
        await self._http.delete(f"{self._resolve_path()}/download")
