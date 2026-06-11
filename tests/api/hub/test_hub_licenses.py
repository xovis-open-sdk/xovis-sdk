"""
Xovis SDK - Hub License Integration Tests

Validates the Hub Plane's ability to manage and provision device licenses.
These tests operate within the State & Topology Plane, interacting with the
Xovis HUB Cloud License Management API.
"""

import pytest

from xovis.models.hub_license_auto import BundleType, LicenseStatusResponse


@pytest.mark.asyncio
async def test_get_license_status(real_hub):
    """
    Test retrieving the license statuses for the tenant.

    Verifies that the SDK can successfully fetch license status information
    from the Hub and parse it into `LicenseStatusResponse`.

    Args:
        real_hub (HubClient): A session-scoped Hub client fixture.

    Returns:
        None

    Raises:
        AssertionError: If the response or its status list do not match expected types.
    """
    response = await real_hub.licenses.get_status()
    assert isinstance(response, LicenseStatusResponse)
    assert isinstance(response.license_status_list, list)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_create_license(real_hub):
    """
    Test creating/provisioning a new license on the Hub.

    Verifies the CREATE capability of the Hub Plane by provisioning an
    object detection bundle to a real device. This test is marked as
    destructive and requires real hardware/hub state.

    Args:
        real_hub (HubClient): A session-scoped Hub client fixture.

    Returns:
        None

    Raises:
        AssertionError: If the creation response is null.
        pytest.skip: If no devices are found to test licensing.
    """
    devices_resp = await real_hub.devices.get_devices()
    if not devices_resp.items:
        pytest.skip("No devices found to test licensing.")

    real_mac = devices_resp.items[0].id.root if hasattr(devices_resp.items[0].id, "root") else devices_resp.items[0].id
    bundles = [BundleType.OBJECT_DETECTION]

    response = await real_hub.licenses.create(device_ids=[real_mac], bundle_types=bundles)
    assert response is not None
