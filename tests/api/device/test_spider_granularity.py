"""
Xovis SDK - Spider NUC Hardware Restrictions Tests

Operates within the Tier 1 SDET Testing Matrix.
Validates that lensless hardware profiles (Spider NUCs) correctly restrict
access to physical lens contexts (Scene and Privacy) while maintaining
access to data orchestration and analytics endpoints.
"""

from unittest.mock import MagicMock

import pytest

from xovis.api.core.exceptions import HardwareNotSupportedError
from xovis.api.device.client import DeviceClient, SinglesensorContext


@pytest.fixture
def mock_spider_client() -> MagicMock:
    """
    Provisions a mocked DeviceClient representing a Spider NUC profile.

    Returns:
        MagicMock: A simulated DeviceClient with is_spider set to True.
    """
    client = MagicMock(spec=DeviceClient)
    client.is_spider = True
    client._http_client = MagicMock()
    return client


@pytest.fixture
def mock_sensor_client() -> MagicMock:
    """
    Provisions a mocked DeviceClient representing a standard physical sensor.

    Returns:
        MagicMock: A simulated DeviceClient with is_spider set to False.
    """
    client = MagicMock(spec=DeviceClient)
    client.is_spider = False
    client._http_client = MagicMock()
    return client


def test_spider_nuc_singlesensor_restrictions(mock_spider_client: MagicMock) -> None:
    """
    Validates that Spider NUCs gracefully block access to physical lens resources.

    Args:
        mock_spider_client (MagicMock): The injected Spider NUC client fixture.
    """
    ctx = SinglesensorContext(mock_spider_client)

    assert ctx.update is not None

    with pytest.raises(HardwareNotSupportedError) as excinfo:
        _ = ctx.datapush
    assert "Spider NUCs lack physical lenses" in str(excinfo.value)

    with pytest.raises(HardwareNotSupportedError) as excinfo:
        _ = ctx.analytics
    assert "Spider NUCs lack physical lenses" in str(excinfo.value)

    with pytest.raises(HardwareNotSupportedError) as excinfo:
        _ = ctx.history
    assert "Spider NUCs lack physical lenses" in str(excinfo.value)

    with pytest.raises(HardwareNotSupportedError) as excinfo:
        _ = ctx.scene
    assert "Spider NUCs lack physical lenses" in str(excinfo.value)

    with pytest.raises(HardwareNotSupportedError) as excinfo:
        _ = ctx.privacy
    assert "Spider NUCs lack physical lenses" in str(excinfo.value)


def test_sensor_singlesensor_full_access(mock_sensor_client: MagicMock) -> None:
    """
    Validates that standard physical sensors have full access to all singlesensor contexts.

    Args:
        mock_sensor_client (MagicMock): The injected standard sensor client fixture.
    """
    ctx = SinglesensorContext(mock_sensor_client)

    assert ctx.datapush is not None
    assert ctx.analytics is not None
    assert ctx.history is not None
    assert ctx.update is not None
    assert ctx.scene is not None
    assert ctx.privacy is not None
