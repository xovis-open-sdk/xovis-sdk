"""
Xovis SDK - Smart Device Client Router Tests

Validates the hybrid routing decision logic of the SmartDeviceClient
under varying network connectivity and configuration states.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xovis.api.device.client import DeviceClient, SmartDeviceClient


@pytest.mark.asyncio
async def test_smart_router_local_reachable() -> None:
    """
    Validates that SmartDeviceClient routes directly to a local DeviceClient
    when the local handshake succeeds, bypassing the Hub Cloud tunnel.
    """
    mock_local_device = AsyncMock()
    mock_local_device.__aenter__.return_value = mock_local_device
    mock_local_device.__aexit__ = AsyncMock(return_value=None)

    mock_hub = AsyncMock()

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = SmartDeviceClient(
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
async def test_smart_router_local_fails_hub_succeeds() -> None:
    """
    Validates that SmartDeviceClient falls back to the Hub Cloud proxy tunnel
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
        router = SmartDeviceClient(
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
async def test_smart_router_both_fail() -> None:
    """
    Validates that SmartDeviceClient raises a clean ConnectionError when
    both the local connection and Hub Cloud tunnel fallbacks fail.
    """
    mock_local_device = MagicMock()
    mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Connection timed out"))

    mock_hub = AsyncMock()
    mock_hub.connect_device = AsyncMock(side_effect=Exception("Hub offline"))

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = SmartDeviceClient(
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
async def test_smart_router_no_hub_local_fails() -> None:
    """
    Validates that SmartDeviceClient raises a ConnectionError stating no HubClient
    is available when local connection fails and there is no hub_client fallback.
    """
    mock_local_device = MagicMock()
    mock_local_device.__aenter__ = AsyncMock(side_effect=Exception("Connection timed out"))

    with patch("xovis.api.device.client.DeviceClient", return_value=mock_local_device) as mock_client_cls:
        router = SmartDeviceClient(
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
