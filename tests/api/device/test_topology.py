import pytest
from httpx import Response
from xovis.api.device.client import DeviceClient

@pytest.mark.asyncio
async def test_get_ms_graph_top_down_resolution(respx_mock):
    client = DeviceClient("192.168.1.100", "admin", "pass")

    discovery_payload = {
        "sensors": [
            {"ip": "192.168.1.100", "mac": "00:11:22:33:44:55", "fw_version": "5.0"},
            {"ip": "192.168.1.101", "mac": "AA:BB:CC:DD:EE:FF", "fw_version": "5.0"}
        ]
    }
    respx_mock.get("http://192.168.1.100:80/api/v5/discover/localnetwork").mock(
        return_value=Response(200, json=discovery_payload)
    )

    respx_mock.get("http://192.168.1.100:80/api/v5/multisensors/status").mock(
        return_value=Response(404, json={})
    )

    async with client:
        graph = await client.topology.get_ms_graph()

    assert graph.master_mac == ""
    assert len(graph.children) == 0
    assert len(graph.ip_map) == 2
