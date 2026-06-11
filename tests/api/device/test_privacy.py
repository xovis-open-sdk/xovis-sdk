"""
Xovis SDK - Privacy Management Integration Tests

Validates the privacy mode and RF (Wi-Fi/Bluetooth) privacy configurations
on local edge sensors. Part of the State & Topology Plane's security validation layer.
"""

import pytest

from xovis.models.device_auto import DeviceIdList, PrivacyMode, PrivacySettings


@pytest.mark.asyncio
async def test_privacy_get_privacy_mode(real_device):
    """
    Validates retrieval of the sensor's current privacy mode.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical lens privacy.")

    mode = await real_device.privacy.get_privacy_mode()
    assert isinstance(mode, PrivacyMode)
    assert mode.privacy_mode is not None


@pytest.mark.asyncio
async def test_privacy_get_rf_privacy(real_device):
    """
    Validates retrieval of RF privacy settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical RF privacy.")

    if not await real_device.has_wifi:
        pytest.skip("RF privacy not supported on this hardware (PC2SEL/RUL)")
    rf_settings = await real_device.privacy.get_rf_privacy()
    assert isinstance(rf_settings, PrivacySettings)


@pytest.mark.asyncio
async def test_privacy_get_devices(real_device):
    """
    Validates retrieval of detected devices in the context of RF privacy.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical device observation.")

    if not await real_device.has_wifi:
        pytest.skip("RF privacy not supported on this hardware (PC2SEL/RUL)")
    devices = await real_device.privacy.get_devices()
    assert isinstance(devices, DeviceIdList)
    assert isinstance(devices.devices, list)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_privacy_update_mode(real_device):
    """
    Validates idempotent updating of the privacy mode.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical lens privacy.")

    current_mode = await real_device.privacy.get_privacy_mode()
    test_mode = PrivacyMode(privacy_mode=current_mode.privacy_mode)

    result = await real_device.privacy.update_privacy_mode(test_mode)
    assert isinstance(result, PrivacyMode)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_privacy_reset_mode(real_device):
    """
    Validates resetting the privacy mode to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical lens privacy.")

    await real_device.privacy.reset_privacy_mode()
    mode = await real_device.privacy.get_privacy_mode()
    assert isinstance(mode, PrivacyMode)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_privacy_update_rf_privacy(real_device):
    """
    Validates idempotent updating of RF privacy settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical RF privacy.")

    if not await real_device.has_wifi:
        pytest.skip("RF privacy not supported on this hardware (PC2SEL/RUL)")
    current_rf = await real_device.privacy.get_rf_privacy()
    result = await real_device.privacy.update_rf_privacy(current_rf)
    assert isinstance(result, PrivacySettings)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_privacy_reset_rf_privacy(real_device):
    """
    Validates resetting RF privacy settings to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical RF privacy.")

    if not await real_device.has_wifi:
        pytest.skip("RF privacy not supported on this hardware (PC2SEL/RUL)")
    await real_device.privacy.reset_rf_privacy()
    rf_settings = await real_device.privacy.get_rf_privacy()
    assert isinstance(rf_settings, PrivacySettings)
