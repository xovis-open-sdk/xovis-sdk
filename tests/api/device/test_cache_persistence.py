"""
Xovis SDK - Cache Persistence Tests

Operates within the Tier 1 & Tier 2 SDET Testing Matrix.
Validates the offline-first state persistence mechanism of the ConfigCacheManager.
Ensures that HostStateBucket instances are safely serialized to and deserialized
from disk using non-blocking asynchronous threads.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from xovis.api.device.cache import CacheResource, CacheStrategy, ConfigCacheManager, HostStateBucket


@pytest.fixture
def mock_http_client() -> MagicMock:
    """
    Provisions a mocked HTTP client for isolated cache testing.

    Returns:
        MagicMock: A mock object mimicking the XovisHTTPClient with an async 'get'.
    """
    client = MagicMock()
    client.get = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_manual_save_load(mock_http_client: MagicMock, tmp_path: str) -> None:
    """
    Validates manual serialization and deserialization of the state bucket.

    Args:
        mock_http_client (MagicMock): Injected mocked HTTP client.
        tmp_path (str): Pytest-provided temporary directory path.
    """
    persist_path = str(tmp_path / "cache.json")
    manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )

    manager._state.checksum = "test-checksum"
    manager.singlesensor
    manager._state.contexts["singlesensor"].agents = [CacheResource(id=1, name="TestAgent", type="TEST")]

    await manager.save_to_disk()
    assert os.path.exists(persist_path)

    new_manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )
    await new_manager.load_from_disk()

    assert new_manager._state.checksum == "test-checksum"
    assert len(new_manager.singlesensor.agents) == 1
    assert new_manager.singlesensor.agents[0].name == "TestAgent"


@pytest.mark.asyncio
async def test_auto_load_on_start(mock_http_client: MagicMock, tmp_path: str) -> None:
    """
    Validates automatic offline hydration during the boot lifecycle.

    Args:
        mock_http_client (MagicMock): Injected mocked HTTP client.
        tmp_path (str): Pytest-provided temporary directory path.
    """
    persist_path = str(tmp_path / "cache.json")

    state = HostStateBucket()
    state.checksum = "initial-checksum"
    with open(persist_path, "w") as f:
        f.write(state.model_dump_json())

    manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )

    manager.sync = AsyncMock()
    await manager.start()

    assert manager._state.checksum == "initial-checksum"


@pytest.mark.asyncio
async def test_auto_save_on_sync(mock_http_client: MagicMock, tmp_path: str) -> None:
    """
    Validates automatic disk serialization upon successful network synchronization.

    Args:
        mock_http_client (MagicMock): Injected mocked HTTP client.
        tmp_path (str): Pytest-provided temporary directory path.
    """
    persist_path = str(tmp_path / "cache.json")
    manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"agents": []}
    mock_http_client.get.return_value = mock_resp

    ms_resp = MagicMock()
    ms_resp.json.return_value = []
    mock_http_client.get.side_effect = [ms_resp] + [mock_resp] * 8

    await manager.sync()

    assert os.path.exists(persist_path)
    with open(persist_path) as f:
        data = json.load(f)
        assert "contexts" in data
