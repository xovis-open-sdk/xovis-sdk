"""
Xovis SDK - Tier 1: Smoke & Stateless Routing Tests

Validates that API requests correctly serialize XovisTime parameters
into the outbound HTTP query parameters.
"""

import pytest
import respx
from httpx import Response

from xovis.api.device.client import DeviceClient


@pytest.mark.asyncio
async def test_history_routing_serialization():
    """
    Asserts that get_counts serializes XovisTime into raw integer query parameters.
    """
    client = DeviceClient(host="10.0.0.50", username="admin", password="password")

    # We use respx to mock the sensor's history endpoint
    with respx.mock(base_url="http://10.0.0.50") as respx_mock:
        # Match any request to the logics endpoint
        route = respx_mock.get(url__regex=r"/api/v5/singlesensor/data/history/logics.*")
        route.return_value = Response(200, json={"begin": 1717968000000, "end": 1717971600000, "measurements": []})

        # Execute the call with a relative XovisTime
        await client.singlesensor.history.get_counts(start_time="-1h", end_time="now")

        assert route.called
        params = route.calls.last.request.url.params

        # Assert that 'begin' and 'end' are numeric strings (Unix ms)
        # and NOT the original relative strings
        assert params["begin"].isdigit()
        assert params["end"].isdigit()
        assert int(params["begin"]) < int(params["end"])


@pytest.mark.asyncio
async def test_start_stop_routing_serialization():
    """
    Asserts that get_start_stop_points serializes XovisTime into raw integer query parameters.
    """
    client = DeviceClient(host="10.0.0.50", username="admin", password="password")

    with respx.mock(base_url="http://10.0.0.50") as respx_mock:
        route = respx_mock.get(url__regex=r"/api/v5/singlesensor/data/history/start_stop.*")
        route.return_value = Response(
            200,
            json={
                "begin": 1717968000000,
                "end": 1717971600000,
                "startPoints": [],
                "stopPoints": [],
            },
        )

        await client.singlesensor.history.get_start_stop_points(start_time="-1d", end_time="now")

        assert route.called
        params = route.calls.last.request.url.params
        assert params["begin"].isdigit()
        assert params["end"].isdigit()
