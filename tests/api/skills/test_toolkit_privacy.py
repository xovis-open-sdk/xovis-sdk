import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from xovis.models.hub_auto import Device, DeviceId
from xovis.skills.toolkit import SafetyLevel, XovisAIToolkit


@pytest.mark.asyncio
async def test_toolkit_interception_and_restoration():
    """
    Tier 2 - Boundary Integration Test: Test Toolkit Interception.
    Asserts that hashed arguments are restored before calling the SDK.
    """
    mock_client = MagicMock()
    toolkit = XovisAIToolkit(client=mock_client)

    real_mac = "00:1E:C0:A0:22:35"
    # Seed the privacy session by sanitizing once
    device = Device(id=DeviceId(root=real_mac))
    sanitized = toolkit.privacy_session.sanitize(device)
    mac_hash = sanitized["id"]

    # Mock a tool function
    mock_func = AsyncMock(return_value={"status": "rebooting"})

    # Manually register a mock tool for testing
    class MockArgsModel(BaseModel):
        confirmation: bool
        device_id: str

    toolkit._tools_map["reboot_device"] = {
        "func": mock_func,
        "args_model": MockArgsModel,
        "safety_level": SafetyLevel.RESTRICTED,
    }

    # Execute tool with hash
    await toolkit.execute_tool("reboot_device", {"confirmation": True, "device_id": mac_hash})

    # Verify that the underlying function was called with the REAL mac
    args, kwargs = mock_func.call_args
    assert kwargs["device_id"] == real_mac


@pytest.mark.asyncio
async def test_toolkit_output_sanitization():
    """
    Tier 2 - Boundary Integration Test: Test Output Sanitization.
    Ensures returned JSON contains hashes and NO plaintext PII.
    """
    mock_client = MagicMock()
    toolkit = XovisAIToolkit(client=mock_client)

    real_mac = "00:1E:C0:A0:22:35"
    real_ip = "10.10.10.2"

    # Mock SDK returning a Device model
    mock_device = Device(id=DeviceId(root=real_mac), ip=real_ip, device_name="Test Device")
    mock_func = AsyncMock(return_value=mock_device)

    class EmptyArgs(BaseModel):
        pass

    toolkit._tools_map["get_device"] = {
        "func": mock_func,
        "args_model": EmptyArgs,
        "safety_level": SafetyLevel.OPEN,
    }

    result_json = await toolkit.execute_tool("get_device", {})

    # Assertions
    assert real_mac not in result_json
    assert real_ip not in result_json
    assert "Id_" in result_json
    assert "Device_" in result_json

    # Verify it is valid JSON
    data = json.loads(result_json)
    assert data["id"].startswith("Id_")


@pytest.mark.asyncio
async def test_toolkit_safety_guardrail_block():
    """
    Tier 2 - Boundary Integration Test: Test Safety Guardrail Block.
    Asserts that BLOCKED tools raise PermissionError.
    """
    mock_client = MagicMock()
    toolkit = XovisAIToolkit(client=mock_client)

    # Mock a BLOCKED tool
    class EmptyArgs(BaseModel):
        pass

    toolkit._tools_map["flash_format"] = {
        "func": AsyncMock(),
        "args_model": EmptyArgs,
        "safety_level": SafetyLevel.BLOCKED,
    }

    with pytest.raises(PermissionError) as excinfo:
        await toolkit.execute_tool("flash_format", {})

    assert "is BLOCKED" in str(excinfo.value)
    # Ensure the function was NEVER called
    toolkit._tools_map["flash_format"]["func"].assert_not_called()
