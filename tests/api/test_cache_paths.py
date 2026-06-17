"""
Xovis SDK - Cache Path Resolution and 3-Tier Persistence Tests

Operates within the Tier 1 & Tier 2 SDET Testing Matrix.
Validates the dynamic auto-resolution, directory auto-creation, read-only
fallback, and global system caching for both DeviceClient and HubClient.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.api.device.cache import CachePaths, ConfigCacheManager
from xovis.api.hub.cache import HubCacheManager


def test_cache_paths_properties() -> None:
    """Validates the structure and attributes of the CachePaths helper."""
    assert CachePaths.BASE_DIR == Path("_local_resources")
    assert CachePaths.STATES_DIR == Path("_local_resources/states")
    assert CachePaths.SCHEMAS_DIR == Path("_local_resources/schemas")
    assert CachePaths.SAMPLES_DIR == Path("_local_resources/samples")
    assert CachePaths.DEVICE_STATE == Path("_local_resources/states/device_state.json")
    assert CachePaths.FLEET_STATE == Path("_local_resources/states/hub_fleet_state.json")


def test_get_system_cache_dir() -> None:
    """Validates that get_system_cache_dir resolves path correctly."""
    cache_dir = CachePaths.get_system_cache_dir()
    assert cache_dir is not None
    assert "xovis" in str(cache_dir)


def test_list_available_states(tmp_path, monkeypatch) -> None:
    """Validates that list_available_states discovers states locally and globally."""
    # Setup temporary local directory
    local_states = tmp_path / "local" / "states"
    sys_states = tmp_path / "sys" / "states"

    local_states.mkdir(parents=True, exist_ok=True)
    sys_states.mkdir(parents=True, exist_ok=True)

    # Create dummy files
    (local_states / "state_1.json").write_text("{}")
    (sys_states / "state_2.json").write_text("{}")

    # Patch CachePaths targets
    monkeypatch.setattr(CachePaths, "STATES_DIR", local_states)
    monkeypatch.setattr(CachePaths, "get_system_cache_dir", lambda: tmp_path / "sys")

    states = CachePaths.list_available_states()
    assert "state_1.json" in states
    assert "state_2.json" in states


def test_get_latest_state(tmp_path, monkeypatch) -> None:
    """Validates that get_latest_state returns the newest state based on modification time."""
    local_states = tmp_path / "local" / "states"
    local_states.mkdir(parents=True, exist_ok=True)

    f1 = local_states / "state_old.json"
    f2 = local_states / "state_new.json"

    f1.write_text("{}")
    f2.write_text("{}")

    # Force f2 modification time to be newer
    os.utime(f1, (1000, 1000))
    os.utime(f2, (2000, 2000))

    monkeypatch.setattr(CachePaths, "STATES_DIR", local_states)
    monkeypatch.setattr(CachePaths, "get_system_cache_dir", lambda: tmp_path / "sys")

    latest = CachePaths.get_latest_state()
    assert latest.name == "state_new.json"


@pytest.mark.asyncio
async def test_3_tier_folder_creation_local_success(tmp_path) -> None:
    """Validates Tier 1 of 3-Tier strategy: successful local workspace creation."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    local_target = tmp_path / "_local_resources" / "states" / "state_192_168_1_50.json"

    # Patch CachePaths.BASE_DIR to tmp_path
    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
        patch("xovis.api.device.cache.CachePaths.DEVICE_STATE", tmp_path / "_local_resources" / "states" / "device_state.json"),
    ):
        manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )

        resolved = await manager._resolve_persist_path()
        assert resolved == str(local_target)
        assert local_target.parent.exists()


@pytest.mark.asyncio
async def test_3_tier_folder_creation_fallback_to_sys(tmp_path) -> None:
    """Validates Tier 2 of 3-Tier strategy: fallback to global system cache when local creation fails."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    local_target = tmp_path / "_local_resources" / "states" / "state_192_168_1_50.json"
    sys_target_dir = tmp_path / "sys_cache"
    sys_target = sys_target_dir / "states" / "state_192_168_1_50.json"

    # Mock parent.mkdir to raise PermissionError for local target
    orig_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "_local_resources" in str(self):
            raise PermissionError("Access Denied")
        return orig_mkdir(self, *args, **kwargs)

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
        patch("xovis.api.device.cache.CachePaths.get_system_cache_dir", return_value=sys_target_dir),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )

        resolved = await manager._resolve_persist_path()
        assert resolved == str(sys_target)
        assert sys_target.parent.exists()
        assert not local_target.parent.exists()


@pytest.mark.asyncio
async def test_3_tier_folder_creation_fallback_to_memory(tmp_path) -> None:
    """Validates Tier 3 of 3-Tier strategy: fallback to memory-only caching when all directory creations fail."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    # Force mkdir to always raise OSError
    def mock_mkdir(self, *args, **kwargs):
        raise OSError("Read-only filesystem")

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )

        resolved = await manager._resolve_persist_path()
        assert resolved is None
        assert manager._memory_only is True


@pytest.mark.asyncio
async def test_hub_cache_manager_3_tier(tmp_path) -> None:
    """Validates that HubCacheManager also resolves using the 3-Tier persistence path system."""
    http_mock = MagicMock()
    fleet_state = tmp_path / "_local_resources" / "states" / "hub_fleet_state.json"

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
        patch("xovis.api.device.cache.CachePaths.FLEET_STATE", tmp_path / "_local_resources" / "states" / "hub_fleet_state.json"),
    ):
        manager = HubCacheManager(
            http_client=http_mock,
        )

        resolved = manager._resolve_persist_path()
        assert resolved == str(fleet_state)
        assert fleet_state.parent.exists()


def test_get_system_cache_dir_platforms() -> None:
    """Validates get_system_cache_dir under multiple OS environments."""
    # 1. win32 with LOCALAPPDATA
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {"LOCALAPPDATA": "C:\\MockUser\\AppData\\Local"}),
    ):
        path = CachePaths.get_system_cache_dir()
        assert path == Path("C:\\MockUser\\AppData\\Local\\xovis\\Cache")

    # 2. win32 without LOCALAPPDATA
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {}, clear=True),
        patch("pathlib.Path.home", return_value=Path("C:\\MockUser")),
    ):
        path = CachePaths.get_system_cache_dir()
        assert path == Path("C:\\MockUser\\AppData\\Local\\xovis\\Cache")

    # 3. linux with XDG_CACHE_HOME
    with (
        patch("sys.platform", "linux"),
        patch.dict(os.environ, {"XDG_CACHE_HOME": "/home/mockuser/.custom_cache"}),
    ):
        path = CachePaths.get_system_cache_dir()
        assert path == Path("/home/mockuser/.custom_cache/xovis")

    # 4. linux without XDG_CACHE_HOME
    with (
        patch("sys.platform", "linux"),
        patch.dict(os.environ, {}, clear=True),
        patch("pathlib.Path.home", return_value=Path("/home/mockuser")),
    ):
        path = CachePaths.get_system_cache_dir()
        assert path == Path("/home/mockuser/.cache/xovis")


def test_get_latest_state_no_existing(tmp_path, monkeypatch) -> None:
    """Validates get_latest_state returns DEVICE_STATE when no state files exist."""
    monkeypatch.setattr(CachePaths, "STATES_DIR", tmp_path / "does_not_exist")
    monkeypatch.setattr(CachePaths, "get_system_cache_dir", lambda: tmp_path / "sys_does_not_exist")
    assert CachePaths.get_latest_state() == CachePaths.DEVICE_STATE


@pytest.mark.asyncio
async def test_ensure_directory_or_fallback_value_error(tmp_path) -> None:
    """Validates fallback to get_system_cache_dir() / name when relative_to raises ValueError."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    # External path that is not relative to _local_resources
    external_path = Path("/some/external/path/state.json") if sys.platform != "win32" else Path("D:\\some\\external\\path\\state.json")
    sys_target_dir = tmp_path / "sys_cache"

    # Mock local mkdir to fail
    orig_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "external" in str(self):
            raise OSError("Local write failed")
        return orig_mkdir(self, *args, **kwargs)

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.get_system_cache_dir", return_value=sys_target_dir),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )

        resolved_path = manager._ensure_directory_or_fallback(external_path)
        assert resolved_path == sys_target_dir / "state.json"
        assert sys_target_dir.exists()


@pytest.mark.asyncio
async def test_resolve_persist_path_persistence_dir_exception() -> None:
    """Validates that ConfigCacheManager gracefully handles device info HTTP exception."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"
    http_mock.get = AsyncMock(side_effect=Exception("Connection Refused"))

    manager = ConfigCacheManager(
        http_client=http_mock,
        strategy=None,
        ttl_seconds=60,
        poll_interval=10,
    )
    manager.persistence_dir = "some_persistence_dir"

    resolved = await manager._resolve_persist_path()
    assert resolved is None


@pytest.mark.asyncio
async def test_save_load_to_disk_memory_only() -> None:
    """Validates save_to_disk and load_from_disk return immediately if memory only."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    manager = ConfigCacheManager(
        http_client=http_mock,
        strategy=None,
        ttl_seconds=60,
        poll_interval=10,
    )
    manager._memory_only = True

    # These should not raise or write anything
    await manager.save_to_disk()
    await manager.load_from_disk()


@pytest.mark.asyncio
async def test_save_load_to_disk_success(tmp_path) -> None:
    """Validates successful save_to_disk and load_from_disk flows."""
    http_mock = MagicMock()
    http_mock.base_url = "http://192.168.1.50"

    target_file = tmp_path / "_local_resources" / "states" / "state_192_168_1_50.json"

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
    ):
        manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )

        # Set some data in _state
        manager._state.contexts["default"] = MagicMock()

        await manager.save_to_disk()
        assert target_file.exists()

        # Load it back
        new_manager = ConfigCacheManager(
            http_client=http_mock,
            strategy=None,
            ttl_seconds=60,
            poll_interval=10,
        )
        await new_manager.load_from_disk()
        assert "default" in new_manager._state.contexts


@pytest.mark.asyncio
async def test_hub_cache_save_load_to_disk_success(tmp_path) -> None:
    """Validates HubCacheManager save and load from disk."""
    http_mock = MagicMock()
    fleet_file = tmp_path / "_local_resources" / "states" / "hub_fleet_state.json"

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.STATES_DIR", tmp_path / "_local_resources" / "states"),
        patch("xovis.api.device.cache.CachePaths.FLEET_STATE", fleet_file),
    ):
        manager = HubCacheManager(
            http_client=http_mock,
        )
        manager._memory_only = False

        await manager.save_to_disk()
        assert fleet_file.exists()

        # Load from disk
        new_manager = HubCacheManager(
            http_client=http_mock,
        )
        await new_manager.load_from_disk()
        assert new_manager._state is not None


@pytest.mark.asyncio
async def test_hub_cache_manager_ensure_directory_fallback_value_error(tmp_path) -> None:
    """Validates HubCacheManager relative_to ValueError fallback."""
    http_mock = MagicMock()
    external_path = Path("/some/external/hub/state.json") if sys.platform != "win32" else Path("D:\\some\\external\\hub\\state.json")
    sys_target_dir = tmp_path / "sys_cache"

    orig_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "external" in str(self):
            raise OSError("Local directory write failed")
        return orig_mkdir(self, *args, **kwargs)

    with (
        patch("xovis.api.device.cache.CachePaths.BASE_DIR", tmp_path / "_local_resources"),
        patch("xovis.api.device.cache.CachePaths.get_system_cache_dir", return_value=sys_target_dir),
        patch.object(Path, "mkdir", mock_mkdir),
    ):
        manager = HubCacheManager(
            http_client=http_mock,
        )

        resolved_path = manager._ensure_directory_or_fallback(external_path)
        assert resolved_path == sys_target_dir / "state.json"
        assert sys_target_dir.exists()


def test_get_latest_state_sys_exists(tmp_path, monkeypatch) -> None:
    """Validates get_latest_state when sys_states_dir has files."""
    sys_states = tmp_path / "sys" / "states"
    sys_states.mkdir(parents=True, exist_ok=True)
    f_sys = sys_states / "state_sys.json"
    f_sys.write_text("{}")

    monkeypatch.setattr(CachePaths, "STATES_DIR", tmp_path / "does_not_exist")
    monkeypatch.setattr(CachePaths, "get_system_cache_dir", lambda: tmp_path / "sys")

    latest = CachePaths.get_latest_state()
    assert latest == f_sys
