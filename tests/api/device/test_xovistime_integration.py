"""
Xovis SDK - Tier 2: Stateful API Integration Tests
Validates the integration of XovisTime across Control Plane resources.
"""

import pytest
import respx
from httpx import Response

from xovis.api.device.client import DeviceClient


@pytest.mark.asyncio
@respx.mock
async def test_history_manager_relative_time_integration() -> None:
    """Validates that HistoryManager correctly handles XovisTime in request parameters."""
    respx.get("http://127.0.0.1/api/v5/device/info").mock(return_value=Response(200, json={"fw_version": "5.9.11"}))
    respx.get("http://127.0.0.1/api/v5/singlesensor/data/history/logics").mock(
        return_value=Response(
            200,
            json={
                "begin": 0,
                "end": 0,
                "begin_data": 0,
                "end_data": 0,
                "index_begin": 0,
                "index_end": 0,
                "resolution_ms": 60000,
                "number_of_bins_requested": 1,
                "number_of_bins": 1,
                "config": {"counts": []},
                "bins": [],
            },
        )
    )

    async with DeviceClient("127.0.0.1", "admin", "admin") as client:
        await client.singlesensor.history.get_counts(start_time="-1h", end_time="now")

        request = respx.calls.last.request
        query = request.url.query.decode()
        assert "begin=" in query
        assert "end=" in query

        import re

        begin_match = re.search(r"begin=(\d+)", query)
        end_match = re.search(r"end=(\d+)", query)

        assert begin_match, f"Expected numeric 'begin' in query: {query}"
        assert end_match, f"Expected numeric 'end' in query: {query}"

        begin_val = int(begin_match.group(1))
        end_val = int(end_match.group(1))

        assert end_val > 0
        assert abs((end_val - begin_val) - 3600000) <= 10
