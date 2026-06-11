"""
Xovis SDK - System Management Integration Tests

Validates core system operations such as hardware identification, state reporting,
and maintenance commands (reboot, reset) on local edge sensors.
Part of the State & Topology Plane's infrastructure validation layer.
"""

import pytest

from xovis.models.device_auto import DeviceInfo, DeviceState1


@pytest.mark.asyncio
async def test_system_get_info(real_device):
    """
    Validates retrieval of static hardware and identity metadata.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    info = await real_device.system.get_info()
    assert info.serial is not None
    assert info.fw_version is not None


@pytest.mark.asyncio
async def test_system_get_state(real_device):
    """
    Validates retrieval of the real-time device health and operational state.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    state = await real_device.system.get_state()
    assert state.state is not None
    assert state.details.uptime_sec >= 0


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_system_reboot(real_device):
    """
    Validates successful delivery of the reboot command.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    await real_device.system.reboot()


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_system_reset(real_device):
    """
    Validates successful delivery of the factory reset command.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    await real_device.system.reset()
