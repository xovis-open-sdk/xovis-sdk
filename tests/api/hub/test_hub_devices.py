"""
Xovis SDK - Hub Device Integration Tests

Validates the Hub Plane's ability to manage, query, and categorize devices.
These tests operate within the State & Topology Plane, ensuring the SDK correctly
interfaces with the Xovis HUB Cloud for fleet-wide visibility and management.
"""

import pytest

from xovis.models.hub_auto import Device, DevicesResponse, DeviceUiAccess


@pytest.mark.asyncio
async def test_get_devices(real_hub):
    """
    Test retrieving the list of devices from the Hub.

    Verifies that the SDK can successfully fetch a list of devices and that
    the response is correctly parsed into `DevicesResponse` and `Device` models.

    Args:
        real_hub (HubClient): A session-scoped Hub client fixture.

    Returns:
        None

    Raises:
        AssertionError: If the response or its items do not match expected types.
    """
    response = await real_hub.devices.get_devices()
    assert isinstance(response, DevicesResponse)
    if response.items:
        assert isinstance(response.items, list)
        assert len(response.items) > 0
        assert isinstance(response.items[0], Device)


@pytest.mark.asyncio
async def test_get_device_ui_access(real_hub):
    """
    Test retrieving temporary UI access links for a device.

    Validates that the SDK can generate secure UI tunnel links for devices
    managed by the Hub, supporting both ID-based and name-based lookups.

    Args:
        real_hub (HubClient): A session-scoped Hub client fixture.

    Returns:
        None

    Raises:
        AssertionError: If the response does not match the `DeviceUiAccess` model.
        pytest.skip: If no devices are found in the tenant.
    """
    devices_resp = await real_hub.devices.get_devices()
    if not devices_resp.items:
        pytest.skip("No devices found in tenant to test UI access.")

    real_mac = devices_resp.items[0].id.root if hasattr(devices_resp.items[0].id, "root") else devices_resp.items[0].id

    response = await real_hub.devices.get_device_ui_access(id_or_name=[real_mac])
    assert isinstance(response, DeviceUiAccess)

    if devices_resp.items[0].device_name:
        response_by_name = await real_hub.devices.get_device_ui_access(id_or_name=devices_resp.items[0].device_name)
        assert isinstance(response_by_name, DeviceUiAccess)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_update_device_categories(real_hub):
    """
    Test updating device categories on the Hub.

    Verifies the UPDATE capability of the Hub Plane by adding a category
    to a real device. This test is marked as destructive and requires
    real hardware/hub state.

    Args:
        real_hub (HubClient): A session-scoped Hub client fixture.

    Returns:
        None

    Raises:
        AssertionError: If the update response is null.
        pytest.skip: If no devices are found to test.
    """
    devices_resp = await real_hub.devices.get_devices()
    if not devices_resp.items:
        pytest.skip("No devices found to test category update.")

    real_mac = devices_resp.items[0].id.root if hasattr(devices_resp.items[0].id, "root") else devices_resp.items[0].id
    categories_to_add = ["pytest-category"]

    response = await real_hub.devices.update_categories(id_or_name=[real_mac], categories_to_add=categories_to_add)
    assert response is not None
