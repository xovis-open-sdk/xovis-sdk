"""
Xovis SDK - TUI Path Resolution and State Bucket Tests

Validates that the TUI state buckets and state files are saved in the logical
directories (_local_resources or home) with proper fallbacks.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xovis.tui.screens.bucket_modal import BucketModal
from xovis.tui.screens.fleet_explorer import XovisFleetTable


def test_bucket_modal_target_dir_with_local_resources(tmp_path, monkeypatch) -> None:
    """
    Validates that BucketModal targets '_local_resources' when it exists and is writeable.
    """
    local_res = tmp_path / "_local_resources"
    local_res.mkdir()

    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # Patch Path inside bucket_modal to return our tmp_path / _local_resources
    # when checking for "_local_resources"
    orig_path_init = Path.__new__

    def mock_path_new(cls, *args, **kwargs):
        if args and args[0] == "_local_resources":
            return local_res
        return orig_path_init(cls, *args, **kwargs)

    with patch.object(Path, "__new__", side_effect=mock_path_new):
        modal = BucketModal(suggested_name="test_bucket", device_count=10)
        assert Path(modal.target_dir) == (local_res / "states").resolve()


def test_bucket_modal_target_dir_fallback(tmp_path, monkeypatch) -> None:
    """
    Validates that BucketModal falls back to current working directory
    when '_local_resources' does not exist.
    """
    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # Patch Path.exists to return False when checking for "_local_resources"
    orig_exists = Path.exists

    def mock_exists(self):
        if "_local_resources" in str(self):
            return False
        return orig_exists(self)

    with patch.object(Path, "exists", mock_exists):
        modal = BucketModal(suggested_name="test_bucket", device_count=10)
        assert Path(modal.target_dir).resolve() == tmp_path.resolve()


@pytest.mark.asyncio
async def test_fleet_explorer_bucket_action_path_resolution(tmp_path, monkeypatch) -> None:
    """
    Validates that XovisFleetTable's _on_bucket_action resolves the bucket path
    to '_local_resources' when it exists, or falls back to CWD.
    """
    local_res = tmp_path / "_local_resources"
    local_res.mkdir()

    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # We mock the HubClient and its cache export/import
    mock_hub = MagicMock()
    mock_cache = MagicMock()
    mock_hub.cache = mock_cache

    screen = XovisFleetTable(hub_client=mock_hub)
    screen.notify = MagicMock()

    # Patch Path to return our temp local_res
    orig_path_init = Path.__new__

    def mock_path_new(cls, *args, **kwargs):
        if args and args[0] == "_local_resources":
            return local_res
        return orig_path_init(cls, *args, **kwargs)

    with patch.object(Path, "__new__", side_effect=mock_path_new):
        # Trigger save action
        mock_input = MagicMock()
        mock_input.value = ""
        mock_table = MagicMock()
        mock_table.rows = {}

        def query_one_mock(selector, *args, **kwargs):
            from textual.widgets import DataTable, Input

            if selector in (Input, "Input") or (isinstance(selector, type) and issubclass(selector, Input)):
                return mock_input
            return mock_table

        screen.query_one = query_one_mock
        screen._on_bucket_action(("save", "my_test_view"))

        # Check that export_to_file was called with path in local_res / "states"
        expected_path = local_res / "states" / "my_test_view.state.json"
        mock_cache.export_to_file.assert_called_once()
        called_path = Path(mock_cache.export_to_file.call_args[0][0])
        assert called_path.resolve() == expected_path.resolve()


@pytest.mark.asyncio
async def test_fleet_explorer_tui_state_home_resolution(tmp_path, monkeypatch) -> None:
    """
    Validates that XovisFleetTable saves and loads the TUI state using Path.home().
    """
    # Mock the home directory to tmp_path
    monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(tmp_path))
    with patch.object(Path, "home", return_value=tmp_path):
        screen = XovisFleetTable(hub_client=MagicMock())
        mock_input = MagicMock()
        mock_input.value = ""
        screen.query_one = MagicMock(return_value=mock_input)
        screen.notify = MagicMock()
        screen._fleet_data = []
        screen._save_tui_state()

        expected_state_file = tmp_path / ".xovis_tui_state.json"
        assert expected_state_file.exists()
