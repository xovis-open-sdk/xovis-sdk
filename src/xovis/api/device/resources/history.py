"""
Xovis SDK - History Management Resource

Operates within the Control Plane.
Provides the implementation for retrieving historical counting data,
start/stop spatial tracking coordinates, and diagnostic memory states
from local edge sensors. Critical for Layer 3/4 spatial analytics and
Geometry Optimization (Module C).
"""

from typing import TYPE_CHECKING, Any, Optional

from xovis.models.device import (
    HeatHeightMap,
    HistoryQuery,
    HistoryStatus,
    StartStopPoints,
    StartStopQuery,
    TimeFormat,
)
from xovis.utils.time import XovisTime

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class HistoryManager:
    """
    Manages historical data retrieval for the single-sensor context.

    This manager abstracts the complex time-series databases of the edge sensor.
    It exposes aggregated logic measurements, start/stop tracking coordinates,
    spatial heat/height maps, and underlying database diagnostic statuses.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the HistoryManager.

        Args:
            client (DeviceClient): The parent device client instance providing
                authenticated HTTPX connection pooling.
            target_id (Optional[str]): The multisensor target ID, if applicable.
        """
        self._client = client
        self._http = client._http_client
        self.target_id = target_id

    def _resolve_path(self) -> str:
        """
        Resolves the base API path based on the current isolated context.

        Returns:
            str: The resolved API endpoint path.
        """
        # CRITICAL FIX 1: History endpoints reside under /data/history, not /analysis/history
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}/data/history"
        return "/api/v5/singlesensor/data/history"

    async def get_status(self) -> HistoryStatus:
        """
        Retrieves the diagnostic status of the historical data storage.

        Crucial for Autonomous Maintenance to monitor database capacity,
        retention times, and ensure the sensor has not stopped persisting data.

        Returns:
            HistoryStatus: Bridge model containing capacity metrics
                and stored data limits.
        """
        response = await self._http.get(f"{self._resolve_path()}/status")
        return HistoryStatus.model_validate(response.json())

    async def get_counts(
        self,
        start_time: XovisTime,
        end_time: XovisTime = "now",
        resolution: int = 0,
        logic_id: Optional[int] = None,
        time_format: TimeFormat = TimeFormat.RFC3339,  # RFC3339 avoids Pydantic ms/s OverflowErrors
        include_empty: bool = False,
    ) -> Any:
        """
        Retrieves historical logic counts for a specified time interval.

        Args:
            start_time (XovisTime): Begin of time interval (Unix ms or relative).
            end_time (XovisTime): End of time interval (Unix ms or relative).
                Defaults to "now".
            resolution (int): Aggregation resolution in minutes. Defaults to 0 (AUTO).
            logic_id (Optional[int]): If provided, filters the payload to only include
                data for a specific logic ID, significantly reducing network overhead.
            time_format (TimeFormat): The time format for the output data. Defaults to RFC3339.
            include_empty (bool): Whether to include empty bins where data is missing.

        Returns:
            HistoryLogics: Bridge model containing the time-series bins.
        """
        # We utilize the HistoryQuery model to validate and normalize parameters.
        # This ensures that XovisTime offsets (e.g., '-1h') are converted to Unix ms.
        query = HistoryQuery(
            begin=start_time,
            end=end_time,
            resolution_min=resolution,
            time_format=time_format,
            include_empty=include_empty,
        )

        # exclude_unset=True ensures we don't pass default None values to HTTPX
        params = query.model_dump(mode="json", exclude_unset=True, by_alias=True)

        # CRITICAL FIX 3: ARCHITECTURE.md Strict Query Parameter Serialization
        # Overwrite native Python booleans to lowercase strings to prevent Edge HTTP 500s.
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = "true" if value else "false"

        endpoint = f"{self._resolve_path()}/logics"
        if logic_id is not None:
            endpoint += f"/{logic_id}"

        response = await self._http.get(endpoint, params=params)
        return self._client.models.HistoryLogics.model_validate(response.json())

    async def get_start_stop_points(self, start_time: XovisTime, end_time: XovisTime = "now", max_points: int = 1000) -> Any:
        """
        Retrieves the 3D coordinates where tracks first appeared and terminated.

        Essential for the Geometry Optimization Agent to mathematically detect
        lines placed too deep or zones missing track intersections.

        Args:
            start_time (XovisTime): Begin of time interval (Unix ms or relative).
            end_time (XovisTime): End of time interval (Unix ms or relative).
            max_points (int): Maximum number of coordinate points to return.

        Returns:
            StartStopPoints: Bridge model containing lists of Start and Stop
                3D coordinate vectors.
        """
        query = StartStopQuery(begin=start_time, end=end_time, max=max_points)
        params = query.model_dump(mode="json", exclude_unset=True, by_alias=True)

        # Apply strict lowercase boolean casting
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = "true" if value else "false"

        response = await self._http.get(f"{self._resolve_path()}/start_stop", params=params)
        return StartStopPoints.model_validate(response.json())

    async def get_heat_map(self) -> HeatHeightMap:
        """
        Retrieves the spatial heat map data array.

        Provides the percentage of time each pixel in the tracking area is
        occupied by an object. Operates on an exponential moving average (24h).

        Returns:
            HeatHeightMap: Bridge model containing the 2D
                floating-point array and mapping metadata.
        """
        response = await self._http.get(f"{self._resolve_path()}/heat_map", params={"data": "true"})
        return HeatHeightMap.model_validate(response.json())

    async def get_height_map(self) -> HeatHeightMap:
        """
        Retrieves the spatial height map data array.

        Provides the average measured height of objects across the tracking area.
        Highly valuable for diagnosing miscalibrated sensor mounting heights.

        Returns:
            HeatHeightMap: Bridge model containing the 2D
                floating-point array and mapping metadata.
        """
        response = await self._http.get(f"{self._resolve_path()}/height_map", params={"data": "true"})
        return HeatHeightMap.model_validate(response.json())

    async def clear_sensor_db(self) -> None:
        """
        Irreversibly deletes all count records and offsets in the sensor database.

        CRITICAL: This resets all outputs for logic data. It should only be executed
        by an agent if explicitly authorized under the CRITICAL safety guardrails.

        Returns:
            None
        """
        await self._http.delete(f"{self._resolve_path()}/sensor_db")
