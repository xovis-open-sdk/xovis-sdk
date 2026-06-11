"""
Xovis SDK - Network Management Integration Tests

Validates the network configuration and state reporting of local edge sensors.
Part of the State & Topology Plane's infrastructure validation layer.
"""

import pytest

from xovis.models.device_auto import (
    Hostname,
    NetworkIpv4Settings,
    NetworkIpv6Settings,
    NetworkState,
)


@pytest.mark.asyncio
async def test_network_get_ipv4(real_device):
    """
    Validates retrieval of IPv4 network settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    ipv4 = await real_device.network.get_ipv4()
    assert ipv4.address is not None


@pytest.mark.asyncio
async def test_network_get_ipv6(real_device):
    """
    Validates retrieval of IPv6 network settings.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    ipv6 = await real_device.network.get_ipv6()
    assert ipv6.address is not None


@pytest.mark.asyncio
async def test_network_get_state(real_device):
    """
    Validates retrieval of the current network operational state.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    state = await real_device.network.get_state()
    # Pydantic V2 model_construct might not set fields correctly if they aren't provided in the dict
    # We just want to check if the call succeeded and returned something with details
    assert state.details is not None


@pytest.mark.asyncio
async def test_network_get_hostname(real_device):
    """
    Validates retrieval of the sensor's hostname.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    hostname = await real_device.network.get_hostname()
    assert hostname.hostname is not None


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_network_update_hostname(real_device):
    """
    Validates idempotent updating of the sensor's hostname.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    original_hostname = await real_device.network.get_hostname()

    try:
        new_hostname = Hostname(hostname="XS-TESTING")
        await real_device.network.update_hostname(new_hostname)

        check = await real_device.network.get_hostname()
        assert check.hostname == "XS-TESTING"
    finally:
        await real_device.network.update_hostname(original_hostname)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_network_reset_ipv4(real_device):
    """
    Validates resetting of IPv4 settings to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    await real_device.network.reset_ipv4()
    ipv4 = await real_device.network.get_ipv4()
    assert isinstance(ipv4, NetworkIpv4Settings)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_network_reset_ipv6(real_device):
    """
    Validates resetting of IPv6 settings to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    await real_device.network.reset_ipv6()
    ipv6 = await real_device.network.get_ipv6()
    assert isinstance(ipv6, NetworkIpv6Settings)
