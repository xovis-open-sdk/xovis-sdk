"""
Xovis SDK - Time Configuration Integration Tests

Validates the time settings, NTP synchronization, and timezone management
on local edge sensors. Part of the State & Topology Plane's infrastructure validation layer.
"""

import pytest

from xovis.models.device_auto import TimeSettings, TimeState, Timezones


@pytest.mark.asyncio
async def test_time_get_settings(real_device):
    """
    Validates retrieval of the sensor's current time and NTP settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    settings = await real_device.time.get_settings()
    assert settings is not None


@pytest.mark.asyncio
async def test_time_get_state(real_device):
    """
    Validates retrieval of the sensor's current operational time state.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    state = await real_device.time.get_state()
    assert state is not None


@pytest.mark.asyncio
async def test_time_get_zones(real_device):
    """
    Validates retrieval of supported timezones from the sensor.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    zones = await real_device.time.get_zones()
    assert zones is not None


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_time_update_settings(real_device):
    """
    Validates idempotent updating of the sensor's time settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    current_settings = await real_device.time.get_settings()
    result = await real_device.time.update_settings(current_settings)
    assert result is None or hasattr(result, "ntp")


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_time_reset_settings(real_device):
    """
    Validates resetting the time settings to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    await real_device.time.reset_settings()
    settings = await real_device.time.get_settings()
    assert settings is not None
