"""
Xovis SDK - Unified Device Client Router Tests

Validates the hybrid routing decision logic of the UnifiedDeviceClient
under varying network connectivity and configuration states.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.api.core.exceptions import AmbiguousDeviceNameError
from xovis.api.device.client import DeviceClient, UnifiedDeviceClient


@pytest.mark.asyncio
async def test_unified_router_local_reachable() -> None:
    """
    Validates that UnifiedDeviceClient routes directly to a local DeviceClient
    when the local handshake succeeds, bypassing the Hub Cloud tunnel.
    """
    mock_local_device = AsyncMock()
    mock_local_device.__aenter__.return_value = mock_local_device
    mock_local_device.__aexit__ = AsyncMock(return_value=None)

    mock_hub = AsyncMock()

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = UnifiedDeviceClient(
            mac_address="00:11:22:33:44:55",
            host="192.168.1.100",
            hub_client=mock_hub,
            username="admin",
            password="pass",
        )
        async with router as client:
            assert client is mock_local_device

        assert mock_client_cls.call_count == 2
        mock_hub.connect_device.assert_not_called()


@pytest.mark.asyncio
async def test_unified_router_local_fails_hub_succeeds() -> None:
    """
    Validates that UnifiedDeviceClient falls back to the Hub Cloud proxy tunnel
    when the direct local IP connection fails.
    """
    mock_local_device = MagicMock()
    mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Connection timed out"))

    mock_hub_device = AsyncMock()
    mock_hub_device.__aenter__.return_value = mock_hub_device
    mock_hub_device.__aexit__ = AsyncMock(return_value=None)

    mock_hub = AsyncMock()
    mock_hub.connect_device = AsyncMock(return_value=mock_hub_device)

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = UnifiedDeviceClient(
            mac_address="00:11:22:33:44:55",
            host="192.168.1.100",
            hub_client=mock_hub,
            username="admin",
            password="pass",
        )
        async with router as client:
            assert client is mock_hub_device

        assert mock_client_cls.call_count == 1
        mock_hub.connect_device.assert_called_once_with("00:11:22:33:44:55")


@pytest.mark.asyncio
async def test_unified_router_both_fail() -> None:
    """
    Validates that UnifiedDeviceClient raises a clean ConnectionError when
    both the local connection and Hub Cloud tunnel fallbacks fail.
    """
    mock_local_device = MagicMock()
    mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Connection timed out"))

    mock_hub = AsyncMock()
    mock_hub.connect_device = AsyncMock(side_effect=Exception("Hub offline"))

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = UnifiedDeviceClient(
            mac_address="00:11:22:33:44:55",
            host="192.168.1.100",
            hub_client=mock_hub,
            username="admin",
            password="pass",
        )
        with pytest.raises(ConnectionError) as exc_info:
            async with router:
                pass

        assert "via LAN" in str(exc_info.value)
        assert "Hub offline" in str(exc_info.value)
        assert mock_client_cls.call_count == 1
        mock_hub.connect_device.assert_called_once_with("00:11:22:33:44:55")


@pytest.mark.asyncio
async def test_unified_router_no_hub_local_fails() -> None:
    """
    Validates that UnifiedDeviceClient raises a ConnectionError stating no HubClient
    is available when local connection fails and there is no hub_client fallback.
    """
    mock_local_device = MagicMock()
    mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Connection timed out"))

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = UnifiedDeviceClient(
            mac_address="00:11:22:33:44:55",
            host="192.168.1.100",
            hub_client=None,
            username="admin",
            password="pass",
        )
        with pytest.raises(ConnectionError) as exc_info:
            async with router:
                pass

        assert "offline/unreachable on LAN" in str(exc_info.value)
        assert "no HubClient" in str(exc_info.value)
        assert mock_client_cls.call_count == 1


@pytest.mark.asyncio
async def test_unified_router_named_resolution_success() -> None:
    """
    Validates that UnifiedDeviceClient can resolve a device by name from the Hub cache,
    and then successfully routes to it.
    """
    mock_device = MagicMock()
    mock_device.device_name = "Kitchen-Sensor"
    mock_device.ip = "192.168.1.50"

    mock_id = MagicMock()
    mock_id.root = "00:11:22:33:44:55"
    mock_device.id = mock_id

    mock_hub = AsyncMock()
    mock_hub.cache._state.devices = [mock_device]

    mock_hub_device = AsyncMock()
    mock_hub_device.__aenter__.return_value = mock_hub_device
    mock_hub_device.__aexit__ = AsyncMock(return_value=None)
    mock_hub.connect_device = AsyncMock(return_value=mock_hub_device)

    router = UnifiedDeviceClient(
        name="Kitchen-Sensor",
        hub_client=mock_hub,
    )

    assert router.name == "Kitchen-Sensor"

    with patch("xovis.api.device.client.DeviceClient") as mock_client_cls:
        mock_local_device = MagicMock()
        mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Local connection failed"))
        mock_client_cls.return_value = mock_local_device

        async with router as client:
            assert client is mock_hub_device

        mock_hub.connect_device.assert_called_once_with("00:11:22:33:44:55")


@pytest.mark.asyncio
async def test_unified_router_named_resolution_ambiguous() -> None:
    """
    Validates that UnifiedDeviceClient raises AmbiguousDeviceNameError if multiple
    devices share the exact same name in the Hub cache.
    """
    mock_device1 = MagicMock()
    mock_device1.device_name = "Kitchen-Sensor"
    mock_device1.ip = "192.168.1.50"

    mock_id1 = MagicMock()
    mock_id1.root = "00:11:22:33:44:55"
    mock_device1.id = mock_id1

    mock_device2 = MagicMock()
    mock_device2.device_name = "Kitchen-Sensor"
    mock_device2.ip = "192.168.1.51"

    mock_id2 = MagicMock()
    mock_id2.root = "00:11:22:33:44:56"
    mock_device2.id = mock_id2

    mock_hub = AsyncMock()
    mock_hub.cache._state.devices = [mock_device1, mock_device2]

    router = UnifiedDeviceClient(
        name="Kitchen-Sensor",
        hub_client=mock_hub,
    )

    with pytest.raises(AmbiguousDeviceNameError) as exc_info:
        async with router:
            pass

    assert "Multiple devices found with name" in str(exc_info.value)
