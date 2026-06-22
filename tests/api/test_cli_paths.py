"""
Xovis SDK - CLI Path Resolution and Synchronization Tests

Operates within the Tier 1 & Tier 2 SDET Testing Matrix.
Validates that xovis-cli generate-types paths are resolved logically,
and that the HardwareSyncer saves unified device state files.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.api.device.sync import HardwareSyncer
from xovis.cli import main


@pytest.fixture
def mock_device_client():
    """
    Mocks the DeviceClient for testing HardwareSyncer without physical hardware.

    Returns:
        MagicMock: A mock device client with stubbed cache and version attributes.
    """
    client = MagicMock()
    client.fw_version = "5.9.11"
    client._device_info = {"type": "PC2S", "serial": "12345", "mac": "00:11:22:33:44:55"}

    # Mocking cache and async sync
    cache_mock = MagicMock()
    cache_mock.sync = AsyncMock()
    # Mocking HostStateBucket representation
    from xovis.api.device.cache import HostStateBucket

    cache_mock._state = HostStateBucket()
    client.cache = cache_mock

    # Mocking http client
    http_mock = MagicMock()

    async def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "schemas/datapush" in url:
            resp.text = '{"schema": "mocked_' + url.split("/")[-1] + '"}'
        else:
            resp.text = "openapi: 3.0.0"
        return resp

    http_mock.get = AsyncMock(side_effect=mock_get)
    client._http_client = http_mock

    # Mocking async context manager
    client_cm = MagicMock()
    client_cm.__aenter__ = AsyncMock(return_value=client)
    client_cm.__aexit__ = AsyncMock(return_value=None)

    return client_cm


@pytest.mark.asyncio
async def test_hardware_syncer_unified_state_path(mock_device_client, tmp_path) -> None:
    """
    Validates that HardwareSyncer writes both the IP-specific state file
    and the unified 'device_state.json' file to the resource directory.

    Args:
        mock_device_client: Injected mocked DeviceClient context manager.
        tmp_path: Pytest-provided temporary directory path.
    """
    syncer = HardwareSyncer(host="192.168.1.100", username="admin", password="pass")

    syncer.resource_dir = tmp_path

    with patch("xovis.api.device.sync.DeviceClient", return_value=mock_device_client):
        success = await syncer.warmup()

    assert success is True

    ip_specific_file = tmp_path / "states" / "state_192_168_1_100.json"
    unified_file = tmp_path / "states" / "device_state.json"

    assert ip_specific_file.exists()
    assert unified_file.exists()

    ip_content = ip_specific_file.read_text()
    unified_content = unified_file.read_text()
    assert ip_content == unified_content

    schemas = ["live", "logics", "status", "wifibt"]
    for schema_type in schemas:
        schema_file = tmp_path / "schemas" / "5-9-11" / f"datapush_{schema_type}.json"
        assert schema_file.exists()
        assert schema_type in schema_file.read_text()

    openapi_file = tmp_path / "schemas" / "5-9-11" / "api.yaml"
    fallback_openapi_file = tmp_path / "schemas" / "api.yaml"
    assert openapi_file.exists()
    assert fallback_openapi_file.exists()


def test_cli_path_resolution_order(tmp_path, monkeypatch) -> None:
    """
    Validates the prioritized lookup mechanism for xovis-cli gen-types
    default --source path, following the priority order:
    1. hub_fleet_state.json
    2. device_state.json in local resources
    3. state_*.json in local resources
    4. device_state.json in root / package fallback.
    """
    local_res = tmp_path / "_local_resources"
    local_res.mkdir()

    monkeypatch.chdir(tmp_path)

    from xovis import cli

    monkeypatch.setattr(cli, "Path", lambda *args, **kwargs: Path(*args, **kwargs) if args and args[0] != "_local_resources" else local_res)

    def get_resolved_source():
        with patch.object(sys, "argv", ["xovis-cli", "generate-types", "--dry-run"]):
            with patch("xovis.cli.generate_types") as mock_gen:
                try:
                    cli.main()
                except SystemExit:
                    pass
                if mock_gen.called:
                    return mock_gen.call_args[0][0]
        return None

    pkg_default = get_resolved_source()
    assert pkg_default is not None

    cwd_device_state = tmp_path / "device_state.json"
    cwd_device_state.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(cwd_device_state.resolve())
    cwd_device_state.unlink()

    states_dir = local_res / "states"
    states_dir.mkdir()

    state_file_fallback = local_res / "state_10_0_0_2.json"
    state_file_fallback.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(state_file_fallback)

    state_file = states_dir / "state_10_0_0_1.json"
    state_file.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(state_file)

    dev_state_fallback = local_res / "device_state.json"
    dev_state_fallback.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(dev_state_fallback)

    dev_state = states_dir / "device_state.json"
    dev_state.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(dev_state)

    hub_state_fallback = local_res / "hub_fleet_state.json"
    hub_state_fallback.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(hub_state_fallback)

    hub_state = states_dir / "hub_fleet_state.json"
    hub_state.write_text("{}", encoding="utf-8")
    assert get_resolved_source() == str(hub_state)


def test_cli_gen_types_device_routing() -> None:
    """Verifies that gen-types parses --device and --via-hub correctly."""
    with patch.object(sys, "argv", ["xovis-cli", "gen-types", "--device", "192.168.1.50", "--via-hub", "--dry-run"]):
        with patch("xovis.cli.generate_types") as mock_gen:
            try:
                main()
            except SystemExit:
                pass
            assert mock_gen.called
            kwargs = mock_gen.call_args[1]
            assert kwargs.get("device") == "192.168.1.50"
            assert kwargs.get("via_hub") is True


@pytest.mark.asyncio
async def test_discover_device_ip_by_mac_windows_arp() -> None:
    """Verifies ARP resolution logic works for MAC discovery."""
    import platform

    from xovis.api.device.network_discovery import NetworkDiscoveryService

    with patch("platform.system", return_value="Windows"):
        with patch("subprocess.check_output") as mock_run:
            mock_run.return_value = "  192.168.178.38        00-6e-02-02-7e-64     dynamisch\n"

            ip = await NetworkDiscoveryService.resolve_mac_to_ip("00:6e:02:02:7e:64")
            assert ip == "192.168.178.38"
            mock_run.assert_called_once_with(["arp", "-a"], text=True)


def test_cli_docs_check_docstrings_routing() -> None:
    """Verifies that docs check-docstrings subcommand maps to check_doc_coverage."""

    with patch.object(sys, "argv", ["xovis-cli", "docs", "check-docstrings"]):
        with patch("xovis.cli.check_doc_coverage") as mock_check:
            try:
                main()
            except SystemExit:
                pass
            assert mock_check.called


def test_cli_docs_serve_routing() -> None:
    """Verifies that docs serve subcommand routes with specified parameters."""

    with patch.object(sys, "argv", ["xovis-cli", "docs", "serve", "--host", "127.0.0.1", "--port", "12345"]):
        with patch("xovis.cli.serve_docs") as mock_serve:
            try:
                main()
            except SystemExit:
                pass
            mock_serve.assert_called_once_with("127.0.0.1", 12345)


def test_scan_markdown_files(tmp_path) -> None:
    """Validates recursive Markdown file scanning and folder filtering."""
    from xovis.cli import scan_markdown_files

    (tmp_path / "README.md").write_text("Root doc", encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("Guide doc", encoding="utf-8")

    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "ignored.md").write_text("Ignored", encoding="utf-8")

    scanned = scan_markdown_files(str(tmp_path))
    assert "README.md" in scanned
    assert "docs/guide.md" in scanned
    assert ".venv/ignored.md" not in scanned


def test_serve_docs_server_behavior() -> None:
    """Validates that serve_docs starts server and correctly translates paths."""
    from xovis.cli import serve_docs

    class FakeServer:
        def __init__(self, addr, handler):
            self.server_address = addr
            self.handler = handler

        def serve_forever(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    with patch("http.server.ThreadingHTTPServer", side_effect=FakeServer) as mock_server_cls:
        with patch("webbrowser.open") as mock_open:
            serve_docs("127.0.0.1", 8080)
            assert mock_server_cls.called
            assert mock_open.called

            handler_class = mock_server_cls.call_args[0][1]
            mock_handler = MagicMock()
            mock_handler.path = "/"

            translated_root = handler_class.translate_path(mock_handler, "/")
            assert translated_root.endswith("index.html")

            translated_other = handler_class.translate_path(mock_handler, "/README.md")
            assert translated_other.replace("\\", "/").endswith("README.md")


def test_cli_import_guards_mcp() -> None:
    """Verifies start_mcp handles missing mcp dependency gracefully."""
    from xovis.cli import start_mcp

    with patch.dict("sys.modules", {"mcp": None}):
        with patch("xovis.cli.logger.error") as mock_log:
            start_mcp()
            mock_log.assert_called_once()
            assert "MCP dependencies are missing" in mock_log.call_args[0][0]


def test_cli_import_guards_tui() -> None:
    """Verifies TUI commands handle missing dependencies gracefully."""
    from xovis.cli import start_datapush_studio, start_setup, start_tui

    with patch.dict("sys.modules", {"xovis.tui.app": None, "xovis.api.core.tui": None, "xovis.datapush.transmission_check": None}):
        with patch("xovis.cli.logger.error") as mock_log:
            start_tui()
            assert mock_log.called
            assert "TUI dependencies are missing" in mock_log.call_args[0][0]

            mock_log.reset_mock()
            start_setup()
            assert mock_log.called
            assert "TUI dependencies are missing" in mock_log.call_args[0][0]

            mock_log.reset_mock()
            start_datapush_studio(9000, "TCP")
            assert mock_log.called
            assert "TUI dependencies are missing" in mock_log.call_args[0][0]


def test_cli_import_guards_docs() -> None:
    """Verifies serve_docs handles missing mkdocs dependency gracefully."""
    from xovis.cli import serve_docs

    with patch.dict("sys.modules", {"mkdocs": None}):
        with patch("xovis.cli.logger.error") as mock_log:
            serve_docs("127.0.0.1", 8080)
            mock_log.assert_called_once()
            assert "Documentation dependencies are missing" in mock_log.call_args[0][0]
