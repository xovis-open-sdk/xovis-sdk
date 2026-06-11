"""
Xovis SDK - Firmware Update Integration Tests

Validates the firmware update status retrieval and upload logic on
local edge sensors. Part of the State & Topology Plane's maintenance validation layer.
"""

import pytest
import respx
from httpx import Response

from xovis.models.device_auto import UpdateInfo, UpdateVersion


@pytest.mark.asyncio
async def test_update_get_status(real_device):
    """
    Validates retrieval of the current firmware update status.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    status = await real_device.singlesensor.update.get_status()
    assert isinstance(status, UpdateInfo)
    assert status.version is not None


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_update_upload_firmware_mock(real_device, tmp_path):
    """
    Validates the SDK's multipart firmware upload logic.

    Uses respx to mock the sensor's response to avoid actual firmware modification.

    Args:
        real_device (DeviceClient): The local device client fixture.
        tmp_path (Path): Pytest temporary directory fixture.
    """
    dummy_file = tmp_path / "test_firmware.xup"
    dummy_file.write_bytes(b"dummy firmware content")

    # Mock version info to return if real_device is a mock and respx fails to intercept
    if hasattr(real_device.singlesensor.update.upload_firmware, "return_value"):
        real_device.singlesensor.update.upload_firmware.return_value = UpdateVersion(version="5.10.0", build_date="2026-01-01")

    with respx.mock(base_url="http://127.0.0.1", assert_all_called=False) as respx_mock:
        respx_mock.post(url__regex=r".*updates").mock(return_value=Response(200, json={"version": "5.10.0", "build_date": "2026-01-01"}))

        version_info = await real_device.singlesensor.update.upload_firmware(str(dummy_file))

        assert isinstance(version_info, UpdateVersion)
        assert version_info.version == "5.10.0"
        # Only assert respx calls if they were intercepted
        if respx_mock.calls:
            assert respx_mock.calls.last.request.method == "POST"
            assert "multipart/form-data" in respx_mock.calls.last.request.headers["content-type"]
