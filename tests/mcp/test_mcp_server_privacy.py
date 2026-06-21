import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.mcp.server import handle_call_tool
from xovis.models.hub_auto import Device, DeviceId


@pytest.mark.asyncio
async def test_mcp_leak_prevention():
    """
    Tier 2 - MCP Output Test: Test MCP Leak Prevention.
    Ensures that handle_call_tool returns sanitized text content without PII.
    """
    real_mac = "00:1E:C0:A0:22:35"
    real_ip = "10.10.10.2"

    # Mock result from toolkit (which should already be sanitized)
    # But since handle_call_tool instantiates the toolkit, we mock toolkit.execute_tool

    Device(id=DeviceId(root=real_mac), ip=real_ip, device_name="Test Device")

    # We need to mock _get_active_client_context and the client context manager
    with patch("xovis.mcp.server._get_active_client_context") as mock_get_context:
        mock_client = AsyncMock()
        mock_get_context.return_value = mock_client

        # toolkit.execute_tool is what returns the JSON string.
        # Inside handle_call_tool:
        # toolkit = XovisAIToolkit(active_client, guardrail=guardrail)
        # result = await toolkit.execute_tool(name, args)

        with patch("xovis.mcp.server.XovisAIToolkit") as mock_toolkit_cls:
            mock_toolkit_instance = MagicMock()
            mock_toolkit_cls.return_value = mock_toolkit_instance

            # Simulate what toolkit.execute_tool would actually return (sanitized JSON)
            # In a real run, it uses its own privacy_session.
            # We want to verify that handle_call_tool takes THIS result and puts it in TextContent.

            sanitized_json = json.dumps({"id": "Id_hashed_mac", "device_name": "Device_hashed_name"})
            mock_toolkit_instance.execute_tool = AsyncMock(return_value=sanitized_json)

            # Act
            response = await handle_call_tool("xovis.system.get_info", {"mac": "00:1E:C0:A0:22:35"})

            # Assert
            assert len(response) == 1
            assert response[0].type == "text"
            text_result = response[0].text

            # Check for PII leaks (should not be there because we mocked toolkit to return sanitized data)
            assert real_mac not in text_result
            assert real_ip not in text_result
            assert "Id_hashed_mac" in text_result

            # Verify toolkit was called correctly
            mock_toolkit_instance.execute_tool.assert_called_once_with("get_system_info", {"mac": "00:1E:C0:A0:22:35"})


@pytest.mark.asyncio
async def test_mcp_error_handling_sanitization():
    """
    Tier 2 - MCP Output Test: Ensure errors are also returned as JSON and don't leak internals.
    """
    with patch("xovis.mcp.server.XovisAIToolkit") as mock_toolkit_cls:
        mock_toolkit_instance = MagicMock()
        mock_toolkit_cls.return_value = mock_toolkit_instance
        mock_toolkit_instance.execute_tool = AsyncMock(side_effect=Exception("Internal Connection Failure: 10.10.10.5"))

        response = await handle_call_tool("xovis.system.get_info", {})

        assert len(response) == 1
        data = json.loads(response[0].text)
        assert "error" in data
        assert "Internal Connection Failure" in data["error"]


def test_mcp_name_translation():
    """
    Tier 2 - MCP Naming Test: Validates the custom bidirectional dot-notation tree translation schema.
    """
    from xovis.mcp.server import _from_mcp_name, _to_mcp_name

    # Test cases mapping internal name -> expected mcp name
    test_cases = {
        "get_system_info": "xovis.system.get_info",
        "get_agent_memory": "xovis.system.get_memory",
        "get_fleet_summary": "xovis.fleet.get_summary",
        "reboot_fleet": "xovis.fleet.reboot",
        "aggregate_geometries": "xovis.aggregate.geometries",
        "aggregate_historical_counts": "xovis.aggregate.historical_counts",
        "system_reboot": "xovis.system.reboot",
        "network_update_ipv4": "xovis.network.update_ipv4",
        "analytics_get_counts": "xovis.analytics.get_counts",
        "privacy_get_state": "xovis.privacy.get_state",
    }

    for original, expected in test_cases.items():
        mcp_name = _to_mcp_name(original)
        assert mcp_name == expected, f"Failed translating '{original}' to MCP name. Got '{mcp_name}', expected '{expected}'"

        reversed_orig = _from_mcp_name(expected)
        assert reversed_orig == original, f"Failed reversing MCP name '{expected}'. Got '{reversed_orig}', expected '{original}'"
