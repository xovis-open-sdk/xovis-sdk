"""
Xovis SDK - Time Configuration Resource

Operates within the Control Plane.
Provides comprehensive implementation for managing time synchronization,
NTP clock drift diagnostics, timezones, and manual overrides.
"""

from typing import TYPE_CHECKING, Any, Optional

from xovis.api.core.http import XovisHTTPClient
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class TimeManager:
    """
    Manages time configuration and synchronization state on a Xovis device.

    This manager orchestrates NTP synchronization, timezone management,
    and exposes raw chronological diagnostics to ensure telemetry timestamps
    remain perfectly aligned with downstream enterprise systems.
    """

    def __init__(self, http_client: XovisHTTPClient, client: Optional["DeviceClient"] = None) -> None:
        """
        Initializes the TimeManager.

        Args:
            http_client (XovisHTTPClient): The resilient HTTP client.
            client (Optional[DeviceClient]): The parent DeviceClient instance.
        """
        self._http = http_client
        self._client = client
        self._base_path = "/api/v5/time"

    @property
    def models(self):
        """Returns the strictly validated Pydantic models for the current firmware."""
        return self._client.models if self._client else stable_models

    async def get_zones(self) -> Any:
        """
        Retrieves the list of available timezones supported by the device.

        Returns:
            Timezones: A collection of supported timezone identifiers
                (e.g., 'UTC', 'America/New_York').
        """
        response = await self._http.get(f"{self._base_path}/zones")
        return self.models.Timezones.model_validate(response.json())

    async def get_settings(self) -> Any:
        """
        Retrieves the current global time configuration.

        Provides insight into whether the device is acting as an NTP client,
        an NTP server, or both, alongside its configured upstream peers.

        Returns:
            TimeSettings: The validated time and NTP configuration model.
        """
        response = await self._http.get(self._base_path)
        return self.models.TimeSettings.model_validate(response.json())

    async def update_settings(self, settings: Any) -> None:
        """
        Updates the global time configuration.

        Allows agents to dynamically inject new NTP peers or change the timezone
        if the device is relocated.

        Args:
            settings (TimeSettings): The updated time configuration model.
        """
        await self._http.put(self._base_path, json=settings)

    async def reset_settings(self) -> None:
        """
        Resets the time configuration to factory defaults.

        Default state falls back to UTC with 'pool.ntp.org' as the primary
        upstream peer and NTP server capabilities disabled.
        """
        await self._http.delete(self._base_path)

    async def set_manual_time(self, time_settings: Any) -> None:
        """
        Manually forces the current device time.

        CRITICAL: This endpoint will fail with a 412 Precondition Failed error
        if the device currently has NTP enabled. Agents must first disable NTP
        via `update_settings` before invoking this method.

        Args:
            time_settings (TimeManualSettings): The manual time details containing
                either `time_utc` or `time_local`.
        """
        await self._http.put(f"{self._base_path}/manual", json=time_settings)

    async def get_state(self) -> Any:
        """
        Retrieves the highly detailed operational state of the time service.

        Crucial for Autonomous Maintenance (Module D). Agents can poll this
        endpoint to monitor `ntp_rms_offset`, `ntp_root_delay`, and identify
        peers marked as `FALSETICKER` or `UNREACHABLE`.

        Returns:
            TimeState: The runtime time synchronization status and source health.
        """
        response = await self._http.get(f"{self._base_path}/state")
        return self.models.TimeState.model_validate(response.json())

    async def get_stamp(self) -> str:
        """
        Retrieves a raw UNIX timestamp directly from the OS-level clock.

        This is an undocumented diagnostic endpoint useful for latency-sensitive
        ping tests between the Hub and the Edge to calculate transit delay.

        Returns:
            str: The raw plaintext timestamp string.
        """
        response = await self._http.get(f"{self._base_path}/stamp")
        return response.text

    async def get_verbose_diagnostics(self) -> str:
        """
        Retrieves raw, verbose NTP daemon logs directly from the Edge OS.

        This is an undocumented diagnostic endpoint providing deep Chrony/NTPd
        output, allowing LLM agents to perform advanced root-cause analysis on
        time synchronization failures.

        Returns:
            str: The raw plaintext verbose diagnostic output.
        """
        response = await self._http.get(f"{self._base_path}/verbose")
        return response.text
