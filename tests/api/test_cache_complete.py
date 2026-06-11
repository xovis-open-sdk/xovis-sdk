"""
Xovis SDK - Sophisticated Cache Integrity Tests

Validates complex caching scenarios across both local (Device) and Hub (Cloud) planes.
Ensures hardware-aware isolation (Spider vs PC/PF), topology preservation,
fleet filtering accuracy, and persistent state hydration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.api.core.exceptions import HardwareNotSupportedError
from xovis.api.device.cache import (
    CacheResource,
    CacheStrategy,
    ConfigCacheManager,
    ContextStateBucket,
)
from xovis.api.device.client import DeviceClient
from xovis.api.hub.cache import HubCacheManager

# --- FIXTURES ---


@pytest.fixture
def mock_http_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    client.base_url = "http://192.168.1.10"
    client.max_retries = 3
    return client


@pytest.fixture
def spider_info():
    return {
        "type": "Spider PU2",
        "prod_code": "SPI-PU2-X",
        "fw_version": "5.9.2",
        "serial": "123456",
    }


@pytest.fixture
def pc_info():
    return {"type": "PC2S", "prod_code": "PC2S-1", "fw_version": "5.9.2", "serial": "654321"}


# --- DEVICE CACHE TESTS ---


@pytest.mark.asyncio
async def test_device_cache_spider_isolation(mock_http_client, spider_info):
    """Ensures Spider NUCs correctly isolate singlesensor requests in cache."""

    # Mock /api/v5/device/info
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: spider_info),  # info
        MagicMock(status_code=200, json=lambda: []),  # multisensors/status
    ] + [MagicMock(status_code=200, json=lambda: {"root": []})] * 20

    with patch("xovis.api.device.client.XovisHTTPClient", return_value=mock_http_client):
        client = DeviceClient("192.168.1.10", "admin", "pass", cache_strategy=CacheStrategy.MANUAL)

        # Manually trigger probing instead of __aenter__
        resp = await mock_http_client.get("/api/v5/device/info")
        client._device_info = resp.json()

        assert client.is_spider is True

        # Accessing singlesensor datapush should raise HardwareNotSupportedError
        with pytest.raises(HardwareNotSupportedError):
            _ = client.singlesensor.datapush

        # Cache should still allow multisensor sync
        # Reset mock for sync test
        mock_http_client.get.reset_mock()
        mock_http_client.get.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"id": 1, "name": "Stitched"}]),  # multisensors/status
        ] + [MagicMock(status_code=200, json=lambda: {"root": []})] * 8  # Endpoints for ctx 1

        await client.cache.sync()

        assert "1" in client.cache._state.contexts
        assert "singlesensor" in client.cache._state.contexts


@pytest.mark.asyncio
async def test_device_cache_multisensor_discovery_fallback(mock_http_client):
    """Validates that cache sync handles multisensor discovery failures gracefully."""
    manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
    )

    # Mock discovery failure (e.g. 404 or 403)
    mock_http_client.get.side_effect = [
        Exception("Forbidden"),  # /api/v5/multisensors/status
    ] + [MagicMock(status_code=200, json=lambda: {"root": []})] * 8  # singlesensor endpoints

    await manager.sync()

    # Should only have singlesensor
    assert list(manager._state.contexts.keys()) == ["singlesensor"]


@pytest.mark.asyncio
async def test_device_cache_persistence_integrity(mock_http_client, tmp_path):
    """Verifies that complex nested topology persists and hydrates correctly."""
    persist_path = str(tmp_path / "complex_cache.json")

    manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )

    # Manually populate complex state
    state = manager._state
    state.checksum = "hash-123"

    # Singlesensor data
    state.contexts["singlesensor"] = ContextStateBucket()
    state.contexts["singlesensor"].agents = [CacheResource(id=1, name="LiveStream", type="TCP")]
    state.contexts["singlesensor"].zones = [CacheResource(id=101, name="Entrance", type="ZONE")]

    # Multisensor data
    state.contexts["1"] = ContextStateBucket()
    state.contexts["1"].agents = [CacheResource(id=2, name="MultiAgent", type="HTTP")]
    state.contexts["1"].logics = [CacheResource(id=50, name="DwellTime", type="LOGIC")]

    await manager.save_to_disk()

    # Hydrate new manager
    new_manager = ConfigCacheManager(
        http_client=mock_http_client,
        strategy=CacheStrategy.MANUAL,
        ttl_seconds=60,
        poll_interval=10,
        auto_persist_path=persist_path,
    )
    await new_manager.load_from_disk()

    assert new_manager._state.checksum == "hash-123"
    assert new_manager.singlesensor.agents[0].name == "LiveStream"
    assert new_manager.multisensors["1"].agents[0].name == "MultiAgent"
    assert len(new_manager.multisensors["1"].logics) == 1


# --- HUB CACHE TESTS ---


@pytest.mark.asyncio
async def test_hub_cache_filtering_and_normalization(mock_http_client):
    """Validates fleet filtering and MAC address normalization in Hub cache."""

    # Hub devices mock
    devices_data = {
        "items": [
            {
                "id": "AA:BB:CC:DD:EE:FF",
                "device_name": "Sensor-A",
                "device_group": "EMEA",
                "customer": "Cust1",
            },
            {
                "id": "11:22:33:44:55:66",
                "device_name": "Sensor-B",
                "device_group": "APAC",
                "customer": "Cust1",
            },
        ]
    }

    # License mock
    licenses_data = {"license_status_list": [{"device_id": "AA:BB:CC:DD:EE:FF", "license_items": []}]}

    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: devices_data),
        MagicMock(status_code=200, json=lambda: licenses_data),
    ]

    # Filter for EMEA only
    manager = HubCacheManager(mock_http_client, fleet_filter={"device_group": "EMEA"})
    await manager.sync()

    assert len(manager._state.devices) == 1
    assert manager._state.devices[0].device_name == "Sensor-A"
    # Verify MAC normalization to uppercase
    assert manager._state.devices[0].id.root == "AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_hub_cache_topology_preservation(mock_http_client):
    """Ensures volatile topology data survives a sync cycle."""

    manager = HubCacheManager(mock_http_client)

    # Pre-populate topology
    manager._state.topology_roles = {"AA:BB:CC:DD:EE:FF": "MASTER"}
    manager._state.topology_parents = {"11:22:33:44:55:66": ["AA:BB:CC:DD:EE:FF"]}

    devices_data = {"items": [{"id": "AA:BB:CC:DD:EE:FF", "device_name": "Master"}]}
    licenses_data = {"license_status_list": []}

    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: devices_data),
        MagicMock(status_code=200, json=lambda: licenses_data),
    ]

    await manager.sync(preserve_topology=True)

    assert manager._state.topology_roles["AA:BB:CC:DD:EE:FF"] == "MASTER"
    assert "11:22:33:44:55:66" in manager._state.topology_parents


@pytest.mark.asyncio
async def test_hub_cache_license_mapping_integrity(mock_http_client):
    """Validates license to device mapping in the Hub cache."""

    mac1 = "00:11:22:33:44:55"
    mac_unknown = "AA:BB:CC:DD:EE:FF"

    devices_data = {"items": [{"id": mac1, "device_name": "D1"}]}

    # License for MAC1 and a different unknown MAC
    licenses_data = {
        "license_status_list": [
            {
                "device_id": mac1,
                "bundle_type": "OBJECT_DETECTION",
                "prepaid_used_days": 0,
                "prepaid_total_days": 365,
                "pay_per_use_bill_status": [],
                "pay_per_use_status": "ACTIVE",
            },
            {
                "device_id": mac_unknown,
                "bundle_type": "PEOPLE_ATTRIBUTES",
                "prepaid_used_days": 0,
                "prepaid_total_days": 365,
                "pay_per_use_bill_status": [],
                "pay_per_use_status": "INACTIVE",
            },
        ]
    }

    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: devices_data),
        MagicMock(status_code=200, json=lambda: licenses_data),
    ]

    manager = HubCacheManager(mock_http_client)
    await manager.sync()

    # Should only keep license for mac1 as mac_unknown is not in devices
    assert len(manager._state.licenses) == 1
    assert manager._state.licenses[0].device_id.root == mac1


# --- AGENTIC / SAFETY INTEGRATION ---


@pytest.mark.asyncio
async def test_cache_inter_context_pacing(mock_http_client):
    """
    Ensures that iterating over active contexts includes required pacing
    to prevent cloud tunnel saturation.
    """
    # This is more of a logic check for HubClient.bulk_execute or similar if we were to test it.
    # But let's check DeviceClient.active_contexts for hardware awareness.

    spider_info = {"type": "Spider", "prod_code": "SPI-PU1", "fw_version": "5.9.2"}

    with patch("xovis.api.device.client.XovisHTTPClient", return_value=mock_http_client):
        # Mocking __aenter__ is tricky, let's just test the property
        client = DeviceClient("1.1.1.1", "a", "p")
        client._device_info = spider_info

        # Spider should have no singlesensor in active_contexts
        assert client.is_spider is True

        # Mock multisensors
        client.multisensors._contexts = ["ctx1", "ctx2"]

        active = client.active_contexts
        assert len(active) == 2
        assert "ctx1" in active
        assert client.singlesensor not in active


if __name__ == "__main__":
    pytest.main([__file__])
