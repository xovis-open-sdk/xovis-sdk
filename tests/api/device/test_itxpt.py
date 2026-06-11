"""
Xovis SDK - ITxPT Integration Tests

Validates the configuration and state reporting of the ITxPT (Information
Technology for Public Transport) service on local edge sensors.
Part of the State & Topology Plane's configuration validation.
"""

import pytest

from xovis.models.device_auto import ItxptConfig, ItxptServicesState, ItxptState


@pytest.mark.asyncio
async def test_itxpt_get_config(real_device):
    """
    Validates retrieval of the ITxPT configuration.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_itxpt():
        pytest.skip("ITxPT not supported on this hardware")
    config = await real_device.itxpt.get_config()
    assert config is not None


@pytest.mark.asyncio
async def test_itxpt_get_state(real_device):
    """
    Validates retrieval of the ITxPT operational state.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_itxpt():
        pytest.skip("ITxPT not supported on this hardware")
    state = await real_device.itxpt.get_state()
    assert state is not None


@pytest.mark.asyncio
async def test_itxpt_get_services_state(real_device):
    """
    Validates retrieval of the ITxPT services runtime status.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_itxpt():
        pytest.skip("ITxPT not supported on this hardware")
    state = await real_device.itxpt.get_services_state()
    assert state is not None


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_itxpt_config_toggle(real_device):
    """
    Validates toggling the ITxPT enabled state.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_itxpt():
        pytest.skip("ITxPT not supported on this hardware")
    original_config = await real_device.itxpt.get_config()

    try:
        new_config = original_config.model_copy(deep=True)
        new_config.itxpt_enabled = not original_config.itxpt_enabled

        await real_device.itxpt.update_config(new_config)
        updated = await real_device.itxpt.get_config()
        assert updated.itxpt_enabled == new_config.itxpt_enabled

    finally:
        await real_device.itxpt.update_config(original_config)
        restored = await real_device.itxpt.get_config()
        assert restored.itxpt_enabled == original_config.itxpt_enabled
