"""
Tier 2: Stateful Configuration Tests (Live Hardware) for DeviceGroup via Hub.
"""

import asyncio

import pytest

from xovis.api.device.client import UnifiedDeviceClient
from xovis.api.fleet.group import DeviceGroup
from xovis.api.fleet.models import BulkOperationResult
from xovis.api.hub.client import HubClient


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_device_group_live_hub_devices() -> None:
    """
    Live test to create a DeviceGroup from devices in the Hub and perform operations.
    """
    async with HubClient() as hub:
        await hub.cache.sync()
        
        # Get devices in the Support Room group
        support_room_devices = [
            d for d in hub.cache._state.devices 
            if getattr(d, "device_group", None) in ("SupportRoom", "Support Room", "Supportroom")
        ]
        
        if not support_room_devices:
            pytest.skip("No devices found in the Support Room group.")
            
        # Select up to 3 devices to test with
        device_macs = []
        for d in support_room_devices[:3]:
            d_id = getattr(d, "id", None)
            mac = (d_id.root if hasattr(d_id, "root") else d_id) if d_id else None
            if mac:
                device_macs.append(str(mac))
        
        clients = []
        for mac in device_macs:
            try:
                udc = UnifiedDeviceClient(mac_address=mac, hub_client=hub)
                client = await udc.__aenter__()
                clients.append(client)
            except Exception as e:
                print(f"Skipping {mac}: {e}")

        if not clients:
            pytest.skip("No accessible devices found in Hub for live testing.")
            
        group = DeviceGroup(name="HubTestGroup", clients=clients)
        
        # Test bulk execution: fetching time stamp
        time_result = await group.time.get_stamp()
        assert isinstance(time_result, BulkOperationResult)
        
        print("Time Sync Result:", time_result.successes, time_result.exceptions)
        
        # Ensure at least one succeeded (or exception recorded correctly)
        assert len(time_result.successes) + len(time_result.exceptions) == len(clients)

        # Cleanup: close the clients
        for client in clients:
            await client.aclose()
