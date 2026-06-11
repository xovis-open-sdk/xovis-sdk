"""
Xovis SDK - History Management Integration Tests

Validates the retrieval of historical counting data from local edge sensors.
Part of the State & Topology Plane's telemetry validation layer.
"""

import pytest


@pytest.mark.asyncio
async def test_history_get_counts(real_device):
    """
    Validates that the HistoryManager correctly fetches and parses logic counts.
    Uses the sensor's internal clock to construct the time window.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    # Construction of time window based on sensor's internal clock to prevent drift failures
    state = await real_device.system.get_state()
    # Assume state.time is Unix milliseconds or can be converted.
    # If state.time is not available, we fall back to a safe relative window.
    sensor_now = getattr(state, "time", None)

    if sensor_now:
        end_time = sensor_now
        start_time = end_time - 3600000  # 1 hour ago
    else:
        start_time = "-3600000"
        end_time = "0"

    resolution = "60"

    try:
        history = await real_device.singlesensor.history.get_counts(start_time=start_time, end_time=end_time, resolution=resolution)

        assert history.measurements is not None
    finally:
        # History GET is read-only, but we ensure the client stays healthy
        pass
