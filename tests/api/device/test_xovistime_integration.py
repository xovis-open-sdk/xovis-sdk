"""
Xovis SDK - Tier 2: Stateful API Integration Tests
Validates the integration of XovisTime across Control Plane resources.
"""

import pytest
import respx
from httpx import Response

from xovis.api.device.client import DeviceClient


@pytest.mark.asyncio
async def test_history_manager_relative_time_integration() -> None:
    """Validates that HistoryManager correctly handles XovisTime in request parameters."""
    async with DeviceClient("127.0.0.1", "admin", "admin") as client:
        # We need to wrap the method to enforce Pydantic validation if we want it to
        # auto-convert strings to ints in the method call itself.
        # But wait, the SDK philosophy is high performance.
        # Actually, HistoryManager.get_counts is NOT decorated with @validate_call.
        # So passing a string will stay a string until it hits the params dict.
        # AND THAT IS ACTUALLY GOOD because the Xovis API accepts these strings!
        # HOWEVER, the requirement was to implement a parser to normalize them.
        # Let's see if I should use the parser in the manager too.

        # Mock the history/logics endpoint
        with respx.mock as mock:
            mock.get("http://127.0.0.1/api/v5/singlesensor/data/history/logics").mock(
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

            # If we want normalization at the manager level, we should use validate_call or call the parser manually.
            # But if the API supports it, why normalize?
            # Because the SDK should provide a consistent experience.

            await client.singlesensor.history.get_counts(start_time="-1h", end_time="now")

            request = mock.calls.last.request
            # If it's normalized, these will be Unix MS strings in the URL.
            # -1h = 3600000 ms
            # We check if they are long digits
            query = request.url.query.decode()
            assert "begin=" in query
            assert "end=" in query

            # Extract begin and end values from query
            import re

            begin_match = re.search(r"begin=(\d+)", query)
            end_match = re.search(r"end=(\d+)", query)

            assert begin_match, f"Expected numeric 'begin' in query: {query}"
            assert end_match, f"Expected numeric 'end' in query: {query}"

            begin_val = int(begin_match.group(1))
            end_val = int(end_match.group(1))

            # end_val should be roughly now
            assert end_val > 0
            # begin_val should be roughly 1 hour before end_val
            assert (end_val - begin_val) == 3600000
