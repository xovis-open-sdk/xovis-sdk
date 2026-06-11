from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from rich.text import Text
from textual.widgets import DataTable, Input

from xovis.models.hub_auto import Device, DeviceId, DeviceStatus
from xovis.tui.screens.fleet_explorer import FleetDevice, XovisFleetTable


@pytest.fixture
def mock_hub_client(monkeypatch):
    """Mocks the HubClient to return controlled device data."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client

    device1 = MagicMock(spec=Device)
    device1.device_name = "Kitchen"
    device1.device_group = "Office"
    device1.customer = "Xovis"
    device1.type = "PC2S"
    device1.id = DeviceId(root="00:11:22:33:44:55")
    device1.firmware_version = "5.10.0-ALPHA1-SNAPSHOT-release.5.10-5035-58522cbf32"
    device1.device_status = DeviceStatus.ONLINE

    device2 = MagicMock(spec=Device)
    device2.device_name = "Entry"
    device2.device_group = "Retail"
    device2.customer = "Shop"
    device2.type = "PC3"
    device2.id = DeviceId(root="AA:BB:CC:DD:EE:FF")
    device2.firmware_version = "5.10.0"
    device2.device_status = DeviceStatus.OFFLINE

    mock_client.cache._state.devices = [device1, device2]
    mock_client.cache._state.topology_roles = {"00:11:22:33:44:55": "Master"}
    mock_client.cache._state.topology_parents = {"00:11:22:33:44:55": []}
    mock_client.cache.sync = AsyncMock()

    monkeypatch.setattr("xovis.tui.screens.fleet_explorer.HubClient", MagicMock(return_value=mock_client))
    return mock_client


@pytest.mark.asyncio
async def test_fleet_explorer_hydration(mock_hub_client):
    """Verifies that the fleet explorer correctly hydrates data from the Hub."""
    screen = XovisFleetTable(hub_client=mock_hub_client)

    screen.query_one = MagicMock()
    screen.notify = MagicMock()

    mock_hub_client.cache._state.devices = [
        Device(
            id=DeviceId(root="00:11:22:33:44:55"),
            device_name="Kitchen",
            device_status=DeviceStatus.ONLINE,
            customer_name="Xovis",
            group_name="Office",
            hardware_id="PC2S",
            firmware_version="5.10.0-ALPHA1-git-7963-g9cbf32",
        ),
        Device(
            id=DeviceId(root="AA:BB:CC:DD:EE:FF"),
            device_status=DeviceStatus.ONLINE,
            customer_name="Shop",
            group_name="Retail",
            device_name="Entry",
            hardware_id="PC3",
            firmware_version="5.10.0",
        ),
    ]

    await screen._fetch_hub_data()
    screen._rebuild_fleet_data_from_cache()

    assert len(screen._fleet_data) == 2
    assert screen._fleet_data[0].mac_address == "00:11:22:33:44:55"
    assert screen._fleet_data[0].name == "Kitchen"
    assert screen._fleet_data[0].firmware == "5.10.0-ALPHA1-...cbf32"
    assert screen._fleet_data[0].status == "🟢 ONLINE"
    assert screen._fleet_data[0].ms_role == "Master"
    assert screen._fleet_data[1].mac_address == "AA:BB:CC:DD:EE:FF"
    assert screen._fleet_data[1].firmware == "5.10.0"


@pytest.mark.asyncio
async def test_fleet_explorer_filtering(mock_hub_client):
    """Verifies the universal search / filtering logic."""
    screen = XovisFleetTable(hub_client=mock_hub_client)

    mock_table = MagicMock(spec=DataTable)
    mock_input = MagicMock(spec=Input)
    mock_input.value = ""

    def query_one(selector):
        if selector in (DataTable, "#fleet-table"):
            return mock_table
        if selector in (Input, "#search-input") or (isinstance(selector, type) and issubclass(selector, Input)):
            return mock_input
        return MagicMock()

    screen.query_one = query_one

    # Set data AFTER mocking query_one to avoid reactive watcher failures
    screen._fleet_data = [
        FleetDevice(
            "00:11:22:33:44:55",
            "🟢 ONLINE",
            "Xovis",
            "Office",
            "Kitchen",
            "PC2S",
            "5.9.2",
            "Master",
            "",
        ),
        FleetDevice(
            "AA:BB:CC:DD:EE:FF",
            "🔴 OFFLINE",
            "Shop",
            "Retail",
            "Entry",
            "PC3",
            "5.10.0",
            "Standalone",
            "",
        ),
    ]

    # Test filtering by Name
    screen._apply_filter("Kitchen")
    mock_table.add_row.assert_called()
    assert mock_table.add_row.call_args.kwargs["key"] == "00:11:22:33:44:55"

    # Test Tokenized Chaining (Name + Status)
    mock_table.add_row.reset_mock()
    screen._apply_filter("Kitchen ONLINE")
    mock_table.add_row.assert_called_once()

    # Test Virtual Tag (is:ai)
    mock_table.add_row.reset_mock()
    screen._fleet_data[0].in_ai_scope = True
    screen._apply_filter("is:ai")
    mock_table.add_row.assert_called_once()
    assert mock_table.add_row.call_args.kwargs["key"] == "00:11:22:33:44:55"


@pytest.mark.asyncio
async def test_fleet_explorer_deep_dive(mock_hub_client):
    """Verifies the Deep Dive worker with live API logic mocking."""
    screen = XovisFleetTable(hub_client=mock_hub_client)
    screen.notify = MagicMock()
    screen._apply_filter = MagicMock()
    screen.query_one = MagicMock()

    screen._fleet_data = [
        FleetDevice(
            "00:11:22:33:44:55",
            "🟢 ONLINE",
            "Xovis",
            "Office",
            "Kitchen",
            "PC2S",
            "5.9.2",
            "Unknown",
            "",
        ),
        FleetDevice(
            "AA:BB:CC:DD:EE:FF",
            "🟢 ONLINE",
            "Shop",
            "Retail",
            "Entry",
            "PC3",
            "5.10.0",
            "Unknown",
            "",
        ),
    ]

    # Mock connect_device to return a mock DeviceClient
    mock_device_client = AsyncMock()
    mock_device_client.__aenter__.return_value = mock_device_client
    mock_hub_client.connect_device = AsyncMock(return_value=mock_device_client)

    # Master Role identification check:
    # 1. graph.master_mac == mac (00:11:22:33:44:55) -> YES
    mock_graph = MagicMock()
    mock_graph.master_mac = "00:11:22:33:44:55"
    mock_child1 = MagicMock()
    mock_child1.mac_address = "00:11:22:33:44:55"
    mock_child1.reference = True
    mock_child2 = MagicMock()
    mock_child2.mac_address = "AA:BB:CC:DD:EE:FF"
    mock_child2.reference = False
    mock_graph.children = [mock_child1, mock_child2]

    # Mock the topology manager to return this graph
    mock_device_client.topology.get_ms_graph = AsyncMock(return_value=mock_graph)

    # Run the worker - Only probe device1 (Master)
    # The worker logic will find device2 in the sensors list of device1 and map it as Child
    with patch.dict("os.environ", {"XOVIS_HUB_CLIENT_ID": "id", "XOVIS_HUB_CLIENT_SECRET": "secret"}):
        await screen._worker_deep_dive(["00:11:22:33:44:55"])

    # Verify results
    assert screen._fleet_data[0].mac_address == "00:11:22:33:44:55"
    assert screen._fleet_data[0].is_cached is True
    assert screen._fleet_data[0].ms_role == "Master"

    assert screen._fleet_data[1].mac_address == "AA:BB:CC:DD:EE:FF"
    # is_cached depends on whether it's in the HubClient cache.
    # The worker doesn't explicitly probe it, but _rebuild_fleet_data_from_cache might mark it cached if it finds it.
    assert screen._fleet_data[1].ms_role == "Child"
    assert screen._fleet_data[1].ms_parent_mac == "00:11:22:33:44:55"

    screen.notify.assert_any_call("Deep Dive complete", severity="information")
    screen._apply_filter.assert_called()


@pytest.mark.asyncio
async def test_fleet_explorer_omni_filter(mock_hub_client):
    """Verifies the Omni-Filter mechanics via cell selection."""
    screen = XovisFleetTable(hub_client=mock_hub_client)

    mock_table = MagicMock(spec=DataTable)
    mock_column = MagicMock()
    mock_column.key = "col_status"
    mock_column.label.plain = "Status"
    mock_table.ordered_columns = [mock_column]

    mock_input = MagicMock(spec=Input)
    mock_input.value = ""

    def query_one(selector):
        if selector in (DataTable, "#fleet-table"):
            return mock_table
        if selector in (Input, "#search-input") or (isinstance(selector, type) and issubclass(selector, Input)):
            return mock_input
        return MagicMock()

    screen.query_one = query_one
    screen.notify = MagicMock()
    screen._apply_filter = MagicMock()

    event = MagicMock(spec=DataTable.CellSelected)
    from textual.coordinate import Coordinate

    event.coordinate = Coordinate(row=0, column=0)
    event.value = Text("🟢 ONLINE")

    screen.on_data_table_cell_selected(event)

    assert mock_input.value == "ONLINE"
    screen.notify.assert_called_with("Added filter: ONLINE", severity="information")
    screen._apply_filter.assert_called_with("ONLINE")

    # Test AI Column Toggle ON
    mock_input.value = ""
    mock_column.label.plain = "AI"
    event.value = Text("✓")
    screen.on_data_table_cell_selected(event)
    assert mock_input.value == "is:ai"

    # Test Cache Column Toggle ON
    mock_input.value = "is:ai"
    mock_column.label.plain = "Cache"
    event.value = Text("✓")
    screen.on_data_table_cell_selected(event)
    assert mock_input.value == "is:ai is:cached"

    # Test Additive Chaining (Toggle ON another token)
    mock_input.value = "ONLINE"
    mock_column.label.plain = "Name"
    event.value = Text("Kitchen")
    screen.on_data_table_cell_selected(event)
    assert mock_input.value == "ONLINE Kitchen"
    screen.notify.assert_called_with("Added filter: Kitchen", severity="information")

    # Test selection toggle (Simulate "Sel" column click)
    mock_column.label.plain = "Sel"
    mock_row_key = MagicMock()
    mock_row_key.value = "00:11:22:33:44:55"
    mock_table.coordinate_to_cell_key.return_value = (mock_row_key, MagicMock())

    screen._fleet_data = [
        FleetDevice(
            "00:11:22:33:44:55",
            "🟢 ONLINE",
            "Xovis",
            "Office",
            "Kitchen",
            "PC2S",
            "5.9.2",
            "Standalone",
            "",
        ),
        FleetDevice(
            "AA:BB:CC:DD:EE:FF",
            "🔴 OFFLINE",
            "Shop",
            "Retail",
            "Entry",
            "PC3",
            "5.10.0",
            "Standalone",
            "",
        ),
    ]

    screen.on_data_table_cell_selected(event)
    assert screen._fleet_data[0].is_selected is True
    screen._apply_filter.assert_called()

    # Test Selection-Aware Deep Dive fallback (Selected -> Visible)
    screen.notify.reset_mock()
    with patch("textual.screen.Screen.app", new_callable=PropertyMock) as mock_app_prop:
        mock_app = MagicMock()
        mock_app_prop.return_value = mock_app
        mock_rows = MagicMock()
        mock_rows.keys.return_value = [
            MagicMock(value="00:11:22:33:44:55"),
            MagicMock(value="AA:BB:CC:DD:EE:FF"),
        ]
        mock_table.rows = mock_rows

        screen.action_deep_dive()
        prompt = mock_app.push_screen.call_args[0][0].prompt_text
        assert "1 SELECTED" in prompt

        # Deselect and test fallback
        screen._fleet_data[0].is_selected = False
        screen.action_deep_dive()
        prompt = mock_app.push_screen.call_args[0][0].prompt_text
        # Only 1 device is ONLINE (00:11:22), so prompt says ALL 1 VISIBLE
        assert "ALL 1 VISIBLE" in prompt
        assert "Skipping OFFLINE" in prompt
