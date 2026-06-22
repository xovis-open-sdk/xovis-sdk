"""
Tier 1: Smoke & Stateless Tests (Mocked) for DeviceGroup.
"""

import httpx
import pytest
import respx

from xovis.api.device.client import DeviceClient
from xovis.api.fleet.group import DeviceGroup
from xovis.api.fleet.models import BulkOperationResult


@pytest.fixture
def mock_clients() -> list[DeviceClient]:
    clients = []
    for i in range(5):
        c = DeviceClient(host=f"10.0.0.{i+10}", username="admin", password="password")
        c.name = f"Sensor_{i+10}"
        clients.append(c)
    return clients


@respx.mock
@pytest.mark.asyncio
async def test_device_group_cache_sync(mock_clients: list[DeviceClient]) -> None:
    """
    Assert that `await group.caches.sync()` correctly populates the in-memory cache
    of all 5 DeviceClient objects concurrently.
    """
    group = DeviceGroup(name="TestGroup", clients=mock_clients)

    for i, c in enumerate(mock_clients):
        host = f"10.0.0.{i+10}"
        respx.get(f"http://{host}/api/v5/multisensors/status").respond(
            200, json={"multisensors_status": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/data/push/agents").respond(
            200, json={"agents": [{"id": 1, "name": "Agent1"}]}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/data/push/connections").respond(
            200, json={"connections": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/scene/geometries").respond(
            200, json={"geometries": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/analysis/logics").respond(
            200, json={"logics": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/analysis/modifiers").respond(
            200, json={"modifiers": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/analysis/counters").respond(
            200, json={"counters": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/scene/masks").respond(
            200, json={"scene_masks": []}
        )
        respx.get(f"http://{host}/api/v5/singlesensor/scene/layers").respond(
            200, json={"layers": []}
        )

    result = await group.caches.sync()

    assert isinstance(result, BulkOperationResult)
    assert len(result.successes) == 5
    assert len(result.exceptions) == 0

    for c in mock_clients:
        assert len(c.cache.singlesensor.agents) == 1
        assert c.cache.singlesensor.agents[0].name == "Agent1"


@respx.mock
@pytest.mark.asyncio
async def test_device_group_time_get_stamp(mock_clients: list[DeviceClient]) -> None:
    """
    Assert that calling `await group.time.get_stamp()` correctly wraps the responses
    into a structured BulkOperationResult.
    Intentionally inject a 403 HTTP error on 1 out of the 5 mocks to verify the
    split-brain mitigation correctly isolates the failure.
    """
    group = DeviceGroup(name="TestGroup", clients=mock_clients)

    for i, c in enumerate(mock_clients):
        host = f"10.0.0.{i+10}"
        if i == 2:
            respx.get(f"http://{host}/api/v5/time/stamp").respond(
                403, text="<html><body>Forbidden</body></html>"
            )
        else:
            respx.get(f"http://{host}/api/v5/time/stamp").respond(
                200, json={"stamp": 123456789}
            )

    result = await group.time.get_stamp()

    assert isinstance(result, BulkOperationResult)
    assert len(result.successes) == 4
    assert len(result.exceptions) == 1

    # Exception should be isolated
    failed_host = str(mock_clients[2]._http_client.client.base_url)
    assert failed_host in result.exceptions
    assert isinstance(result.exceptions[failed_host], Exception)
