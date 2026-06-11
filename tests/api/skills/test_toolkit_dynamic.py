import inspect
import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from xovis.skills.toolkit import DeviceClient, SafetyLevel, XovisAIToolkit


@pytest.mark.asyncio
async def test_toolkit_dynamic_discovery():
    """Test that toolkit correctly discovers tools via reflection."""
    # We use a real DeviceClient but mock its internal managers
    # because XovisAIToolkit uses getattr/inspect on it.
    mock_client = MagicMock(spec=DeviceClient)

    # Mock managers with explicit names to ensure dir() works as expected
    mock_system = MagicMock(name="system")
    mock_system.reboot = AsyncMock(name="reboot")
    mock_system.get_status = AsyncMock(name="get_status")
    mock_system.format_flash = AsyncMock(name="format_flash")
    mock_system.reboot_rescue = AsyncMock(name="reboot_rescue")
    mock_system.hard_reset = AsyncMock(name="hard_reset")
    mock_system.reset = AsyncMock(name="reset")

    # Add them to dir() explicitly if needed for some Python versions
    def mock_dir(self=None):
        return ["reboot", "get_status", "format_flash", "reboot_rescue", "hard_reset", "reset"]

    mock_system.__dir__ = mock_dir
    # Ensure attributes are present on the mock itself for dir() in some Python versions
    for m in mock_dir():
        getattr(mock_system, m)

    # ADDITION: Explicitly set the attributes so they are in __dict__ if dir() relies on it
    mock_system.reboot = mock_system.reboot
    mock_system.get_status = mock_system.get_status
    mock_system.format_flash = mock_system.format_flash
    mock_system.reboot_rescue = mock_system.reboot_rescue
    mock_system.hard_reset = mock_system.hard_reset
    mock_system.reset = mock_system.reset

    mock_network = MagicMock(name="network")
    mock_network.update_xovis_support = AsyncMock(name="update_xovis_support")
    mock_network.delete_remote = AsyncMock(name="delete_remote")
    mock_network.update_remote = AsyncMock(name="update_remote")
    mock_network.update_ipv4 = AsyncMock(name="update_ipv4")

    def mock_dir_net(self=None):
        return ["update_xovis_support", "delete_remote", "update_remote", "update_ipv4"]

    mock_network.__dir__ = mock_dir_net
    for m in mock_dir_net():
        getattr(mock_network, m)

    mock_network.update_xovis_support = mock_network.update_xovis_support
    mock_network.delete_remote = mock_network.delete_remote
    mock_network.update_remote = mock_network.update_remote
    mock_network.update_ipv4 = mock_network.update_ipv4

    mock_analytics = MagicMock(name="analytics")
    mock_analytics.get_counts = AsyncMock(name="get_counts")
    mock_analytics.delete_logic = AsyncMock(name="delete_logic")

    def mock_dir_ana(self=None):
        return ["get_counts", "delete_logic"]

    mock_analytics.__dir__ = mock_dir_ana
    for m in mock_dir_ana():
        getattr(mock_analytics, m)

    mock_analytics.get_counts = mock_analytics.get_counts
    mock_analytics.delete_logic = mock_analytics.delete_logic

    mock_history = MagicMock(name="history")
    mock_history.clear_sensor_db = AsyncMock(name="clear_sensor_db")

    def mock_dir_his(self=None):
        return ["clear_sensor_db"]

    mock_history.__dir__ = mock_dir_his
    for m in mock_dir_his():
        getattr(mock_history, m)

    mock_history.clear_sensor_db = mock_history.clear_sensor_db

    mock_client.system = mock_system
    mock_client.network = mock_network
    mock_client.time = MagicMock(name="time")
    mock_client.update = MagicMock(name="update")
    mock_client.users = MagicMock(name="users")
    mock_client.itxpt = MagicMock(name="itxpt")

    # Mock singlesensor for prefix-based routing
    mock_singlesensor = MagicMock(name="singlesensor")
    mock_client.singlesensor = mock_singlesensor
    mock_singlesensor._analytics = mock_analytics
    mock_singlesensor._history = mock_history
    mock_singlesensor._privacy = MagicMock(name="privacy")
    mock_singlesensor.datapush = MagicMock(name="datapush")
    mock_singlesensor._scene = MagicMock(name="scene")

    toolkit = XovisAIToolkit(client=mock_client)

    # Verify discovery
    assert "system_reboot" in toolkit._tools_map
    assert "system_get_status" in toolkit._tools_map
    assert "analytics_get_counts" in toolkit._tools_map
    assert "analytics_delete_logic" in toolkit._tools_map

    # Verify Safety Heuristics
    assert toolkit._tools_map["system_reboot"]["safety_level"] == SafetyLevel.RESTRICTED
    assert toolkit._tools_map["analytics_delete_logic"]["safety_level"] == SafetyLevel.CRITICAL
    assert toolkit._tools_map["system_get_status"]["safety_level"] == SafetyLevel.OPEN

    # Verify Enterprise Safety Policy (New)
    assert toolkit._tools_map["system_format_flash"]["safety_level"] == SafetyLevel.BLOCKED
    assert toolkit._tools_map["network_update_xovis_support"]["safety_level"] == SafetyLevel.BLOCKED
    assert toolkit._tools_map["history_clear_sensor_db"]["safety_level"] == SafetyLevel.CRITICAL


@pytest.mark.asyncio
async def test_toolkit_specialized_blocking():
    """Test specialized blocking logic for Xovis Support."""
    mock_client = MagicMock(spec=DeviceClient)

    # Define a Mock for NetworkManager
    class MockNetworkManager:
        async def update_xovis_support(self, ctrl):
            return {"status": "ok"}

    mock_client.network = MockNetworkManager()
    # Mock other required managers as MagicMocks
    for attr in ["system", "time", "update", "users", "itxpt", "singlesensor"]:
        setattr(mock_client, attr, MagicMock(name=attr))

    toolkit = XovisAIToolkit(client=mock_client)

    # Attempt to disable support -> Should be blocked
    with pytest.raises(PermissionError) as excinfo:
        await toolkit.execute_tool("network_update_xovis_support", {"ctrl": {"enabled": False}})
    assert "Disabling Xovis Support is BLOCKED" in str(excinfo.value)

    # Attempt to enable support -> Should be allowed (but fails later because BLOCKED at guardrail level)
    # Actually, hardcoded_safety sets it to SafetyLevel.BLOCKED entirely!
    # "network_update_xovis_support": SafetyLevel.BLOCKED
    # So it should be blocked regardless of payload now.

    with pytest.raises(PermissionError) as excinfo:
        await toolkit.execute_tool("network_update_xovis_support", {"ctrl": {"enabled": True}})
    assert "is BLOCKED" in str(excinfo.value)


@pytest.mark.asyncio
async def test_toolkit_user_overrides(tmp_path):
    """Test that toolkit applies user safety overrides from config file."""
    config_file = tmp_path / ".xovis_ai_privacy.json"

    config_data = {"tool_mappings": [{"tool": "system_get_status", "safety": "BLOCKED"}]}
    config_file.write_text(json.dumps(config_data))

    # Mock DeviceClient
    mock_client = MagicMock(spec=DeviceClient)
    mock_system = MagicMock(name="system")
    mock_system.get_status = AsyncMock(name="get_status")

    def mock_dir_over(self=None):
        return ["get_status"]

    mock_system.__dir__ = mock_dir_over
    getattr(mock_system, "get_status")
    mock_system.get_status = mock_system.get_status

    mock_client.system = mock_system
    # Mock other required managers as MagicMocks
    for attr in ["network", "time", "update", "users", "itxpt", "singlesensor"]:
        setattr(mock_client, attr, MagicMock(name=attr))

    # We need to trick XovisAIToolkit to look at our tmp_path
    # The code uses a hardcoded path ".Redacted/ai_privacy_config.json"
    # We can temporarily patch the path or change the working directory

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        toolkit = XovisAIToolkit(client=mock_client)
        assert toolkit._tools_map["system_get_status"]["safety_level"] == SafetyLevel.BLOCKED
    finally:
        os.chdir(old_cwd)


@pytest.mark.asyncio
async def test_toolkit_bridge_registration():
    """Test that bridge tools (aggregators) are correctly registered."""
    mock_client = MagicMock(spec=DeviceClient)
    # Mock all managers to None to avoid interference
    for attr in ["system", "network", "time", "update", "users", "itxpt", "singlesensor"]:
        setattr(mock_client, attr, None)

    toolkit = XovisAIToolkit(client=mock_client)

    assert "get_system_info" in toolkit._tools_map
    assert "aggregate_geometries" in toolkit._tools_map
    assert toolkit._tools_map["get_system_info"]["safety_level"] == SafetyLevel.OPEN


@pytest.mark.asyncio
async def test_toolkit_dynamic_execution():
    """Test that execute_tool correctly routes to dynamically discovered methods."""
    mock_client = MagicMock(spec=DeviceClient)

    # We define a class that mimics SystemManager with explicit coroutines
    class MockSystemManager:
        async def reboot(self):
            return {"status": "rebooting"}

        async def get_status(self):
            return {"status": "ok"}

    mock_system = MockSystemManager()
    mock_client.system = mock_system

    # Mock other required managers as None
    for attr in ["network", "time", "update", "users", "itxpt", "singlesensor"]:
        setattr(mock_client, attr, None)

    toolkit = XovisAIToolkit(client=mock_client)

    # Execute the dynamically discovered tool
    result_json = await toolkit.execute_tool("system_reboot", {"mac": "00:11:22:33:44:55"})
    result = json.loads(result_json)

    # Verify execution
    assert result["status"] == "rebooting"


@pytest.mark.asyncio
async def test_toolkit_safety_heuristics_extended():
    """Verify that reboot, delete, update etc have correct safety levels."""
    mock_client = MagicMock(spec=DeviceClient)

    class MockManager:
        async def reboot(self):
            pass

        async def delete_something(self):
            pass

        async def update_something(self):
            pass

        async def get_something(self):
            pass

        async def factory_reset(self):
            pass

    mock_manager = MockManager()
    mock_client.system = mock_manager
    for attr in ["network", "time", "update", "users", "itxpt", "singlesensor"]:
        setattr(mock_client, attr, None)

    toolkit = XovisAIToolkit(client=mock_client)

    assert toolkit._tools_map["system_reboot"]["safety_level"] == SafetyLevel.RESTRICTED
    assert toolkit._tools_map["system_delete_something"]["safety_level"] == SafetyLevel.CRITICAL
    assert toolkit._tools_map["system_update_something"]["safety_level"] == SafetyLevel.RESTRICTED
    assert toolkit._tools_map["system_get_something"]["safety_level"] == SafetyLevel.OPEN
    assert toolkit._tools_map["system_factory_reset"]["safety_level"] == SafetyLevel.CRITICAL
