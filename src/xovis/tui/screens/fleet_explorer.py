import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input

from xovis.api.core.exceptions import XovisAuthError
from xovis.api.hub.cache import HubStateBucket
from xovis.api.hub.client import HubClient
from xovis.tui.screens.bucket_modal import BucketModal
from xovis.tui.screens.confirm_modal import ConfirmModal
from xovis.tui.screens.scanner_modal import ScannerModal


@dataclass
class FleetDevice:
    """Data structure representing a flattened view of a Xovis device.

    This separates the data state from the UI representation.

    Attributes:
        mac_address (str): The MAC address acting as the primary key.
        status (str): The connectivity status.
        customer (str): The assigned customer name.
        group (str): The logical group assignment.
        name (str): The human-readable device name.
        model (str): The hardware model identifier.
        firmware (str): The current firmware version.
        ms_role (str): The topological role (Master, Child, Standalone).
        ms_parent_mac (str): The MAC address of the parent master, if applicable.
        source (str): Origin of the device data (Hub, LAN, Both).
        in_ai_scope (bool): Indicates if the device is targeted for AI queues.
        is_cached (bool): Indicates if the device topology is stored in RAM.
        is_selected (bool): User-toggled selection flag for bulk operations.
        ip_address (str): The IP address of the device.
    """

    mac_address: str
    status: str
    customer: str
    group: str
    name: str
    model: str
    firmware: str
    ms_role: str
    ms_parent_mac: str
    source: str = "Hub"
    in_ai_scope: bool = False
    is_cached: bool = False
    is_selected: bool = False
    ip_address: str = ""


class XovisFleetTable(Screen):
    """Enterprise Fleet Explorer utilizing a faceted flat-grid architecture.

    Replaces nested hierarchies with a high-performance DataTable, universal
    search, and programmatic Click-to-Filter mechanics for topological grouping.
    """

    CSS = """
    #fleet-table {
        height: 1fr;
        border: solid $accent;
    }
    DataTable > .datatable--header {
        text-style: bold;
        color: $warning;
    }
    DataTable > .datatable--column-firmware {
        max-width: 25;
    }
    """

    BINDINGS = [
        Binding("ctrl+f", "focus_search", "Search Fleet", priority=True),
        Binding("ctrl+r", "refresh_fleet", "Refresh", priority=True),
        Binding("ctrl+s", "toggle_select_all", "Select All/None", priority=True),
        Binding("ctrl+l", "local_scan", "Scan LAN", priority=True),
        Binding("ctrl+a", "toggle_ai", "Toggle AI Scope", priority=True),
        Binding("ctrl+d", "deep_dive", "Deep Dive / Cache", priority=True),
        Binding("escape", "app.pop_screen", "Back", priority=True),
        Binding("ctrl+w", "manage_buckets", "Buckets", priority=True),
    ]

    _fleet_data: reactive[list[FleetDevice]] = reactive(list)
    _lan_devices: dict[str, FleetDevice] = {}
    _hub_client: HubClient

    def __init__(self, hub_client: HubClient, **kwargs) -> None:
        """Initializes the fleet explorer screen.

        Args:
            hub_client (HubClient): The authenticated Xovis Hub client.
            **kwargs: Additional keyword arguments for the Screen.
        """
        super().__init__(**kwargs)
        self._hub_client = hub_client
        self._lan_devices = {}

    def compose(self) -> ComposeResult:
        """Hydrates the fleet explorer layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        yield Header()
        with Vertical(id="main-container"):
            yield Input(
                placeholder="Search by MAC, Name, Firmware, Customer, or MS-Parent...",
                id="search-input",
            )
            yield DataTable(id="fleet-table", cursor_type="cell", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initializes the DataTable columns and triggers the initial data fetch."""
        table = self.query_one(DataTable)
        table.add_columns(
            "Src",
            "Sel",
            "AI",
            "Cache",
            "Status",
            "MAC Address",
            "Customer",
            "Group",
            "Name",
            "Model",
            Text("Firmware", justify="left"),
            "MS Role",
            "MS Parent MAC",
        )
        self.action_refresh_fleet()

    async def on_unmount(self) -> None:
        """Ensures reactive states are clean."""
        self._hub_client = None

    def action_focus_search(self) -> None:
        """Focuses the universal search input widget."""
        self.query_one(Input).focus()

    def action_manage_buckets(self) -> None:
        """Opens the State Bucket management modal."""
        suggested = self.query_one(Input).value.strip().replace(" ", "_")
        if not suggested:
            suggested = "default_fleet"

        table = self.query_one(DataTable)
        visible_count = len(table.rows)

        self.app.push_screen(
            BucketModal(suggested_name=suggested, device_count=visible_count),
            self._on_bucket_action,
        )

    def action_refresh_fleet(self) -> None:
        """Triggers the asynchronous fetch via the Xovis HUB Cloud Control Plane.

        Utilizes Textual's worker management to prevent event loop blocking
        and ensures loading states are properly managed.
        """
        table = self.query_one(DataTable)
        table.loading = True
        self.notify("Fetching fleet topology...", severity="information")
        self.run_worker(self._fetch_hub_data(), exclusive=True)

    def _save_tui_state(self) -> None:
        """Persists the AI Whitelist and Cache state to a local JSON file.

        Creates a mapping of MAC addresses to their respective AI and Cache
        states and saves it to ~/.xovis_tui_state.json.
        """
        from pathlib import Path

        state_path = Path.home() / ".xovis_tui_state.json"
        state_map = {}
        for device in self._fleet_data:
            mac_upper = device.mac_address.upper()
            if device.in_ai_scope or device.is_cached:
                state_map[mac_upper] = {
                    "ai": device.in_ai_scope,
                    "cache": device.is_cached,
                }

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state_map, f, indent=4)
        except Exception as e:
            self.notify(f"Failed to save TUI state: {e}", severity="error")

    def _rebuild_fleet_data_from_cache(self) -> None:
        """Maps the internal Hub cache state and local LAN devices to UI FleetDevice objects."""
        if not self._hub_client:
            return

        from pathlib import Path

        state_path = Path.home() / ".xovis_tui_state.json"
        saved_state = {}
        if os.path.exists(state_path):
            try:
                with open(state_path, encoding="utf-8") as f:
                    saved_state = json.load(f)
            except Exception:
                saved_state = {}

        current_states = {d.mac_address.upper(): (d.is_selected, d.is_cached) for d in self._fleet_data}

        fetched_devices = []
        cache = self._hub_client.cache
        for d in cache._state.devices:
            mac_address = (str(d.id.root) if hasattr(d.id, "root") else str(d.id) if d.id else "00:00:00:00:00:00").upper()

            logging.debug(f"UI Rebuild: Hydrating {mac_address}")

            raw_status = getattr(d, "device_status", "UNKNOWN")
            status_val = str(raw_status.value if hasattr(raw_status, "value") else raw_status).upper()
            if "ONLINE" in status_val:
                status_str = "🟢 ONLINE"
            elif "OFFLINE" in status_val:
                status_str = "🔴 OFFLINE"
            else:
                status_str = f"⚪ {status_val}"

            firmware_raw = str(getattr(d, "firmware_version", "Unknown") or "Unknown")
            firmware_display = f"{firmware_raw[:14]}...{firmware_raw[-5:]}" if len(firmware_raw) > 22 else firmware_raw

            device_state = saved_state.get(mac_address, {})
            ms_role = cache._state.topology_roles.get(mac_address, "Unknown")
            ms_parents = cache._state.topology_parents.get(mac_address, [])
            ms_parent_display = ", ".join(ms_parents) if isinstance(ms_parents, (list, tuple)) else str(ms_parents) if ms_parents else ""

            existing_is_selected, existing_is_cached = current_states.get(mac_address, (False, False))

            if ms_role != "Unknown":
                logging.info(f"UI Rebuild: Device {mac_address} has role {ms_role}, marking as cached.")
                existing_is_cached = True
            elif device_state.get("cache"):
                existing_is_cached = True

            device_entry = FleetDevice(
                mac_address=mac_address,
                status=status_str,
                customer=getattr(d, "customer_name", getattr(d, "customer", "Unassigned")) or "Unassigned",
                group=getattr(d, "device_group", "Unassigned") or "Unassigned",
                name=getattr(d, "device_name", getattr(d, "name", "Unknown")) or "Unknown",
                model=getattr(d, "type", getattr(d, "hardware_type", "Unknown")) or "Unknown",
                firmware=firmware_display,
                ms_role=ms_role,
                ms_parent_mac=ms_parent_display,
                source="Hub",
                in_ai_scope=device_state.get("ai", False),
                is_cached=existing_is_cached,
                is_selected=existing_is_selected,
                ip_address=getattr(d, "ip", "") or "",
            )
            fetched_devices.append(device_entry)

        hub_macs = {d.mac_address: d for d in fetched_devices}
        for lan_device in self._lan_devices.values():
            if lan_device.mac_address in hub_macs:
                hub_macs[lan_device.mac_address].source = "Both"
                hub_macs[lan_device.mac_address].ip_address = lan_device.ip_address
            else:
                fetched_devices.append(lan_device)

        self._fleet_data = fetched_devices
        self._apply_filter(self.query_one(Input).value)

    async def _fetch_hub_data(self) -> None:
        """Internal worker to synchronize state with the Hub.

        Hydrates the local state bucket from the Cloud HUB, maps the raw device
        objects to FleetDevice data classes, and updates the reactive property.
        """
        try:
            await self._hub_client.cache.sync(preserve_topology=True)
            self._rebuild_fleet_data_from_cache()

        except XovisAuthError as e:
            self.notify(f"Authentication Failed: {e}", severity="error")
        except Exception as e:
            self.notify(f"Hub Sync Failed: {e}", severity="error")
        finally:
            self.query_one(DataTable).loading = False

    def watch__fleet_data(self, new_data: list[FleetDevice]) -> None:
        """Reactive watcher that rebuilds the table whenever the underlying data changes.

        Args:
            new_data (List[FleetDevice]): The newly fetched fleet data.
        """
        self._apply_filter(self.query_one(Input).value)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Triggers table re-filtering as the user types in the universal search.

        Args:
            event (Input.Changed): The input changed event payload.
        """
        self._apply_filter(event.value)

    def _apply_filter(self, search_term: str) -> None:
        """Filters the DataTable based on the provided search term.

        Supports tokenized chaining and virtual tags (is:ai, is:cached). All tokens
        must be present in the device's searchable string for it to be displayed.

        Args:
            search_term (str): The search string containing one or more tokens.
        """
        table = self.query_one(DataTable)
        table.clear()

        tokens = search_term.lower().split()

        for device in self._fleet_data:
            searchable_string = " ".join(str(val) for val in device.__dict__.values()).lower()

            if device.in_ai_scope:
                searchable_string += " is:ai"
            if device.is_cached:
                searchable_string += " is:cached"

            if all(token in searchable_string for token in tokens):
                src_icon = (
                    Text("☁️ Hub", style="blue")
                    if device.source == "Hub"
                    else Text("🏠 LAN", style="green")
                    if device.source == "LAN"
                    else Text("🔄 Both", style="magenta")
                )
                table.add_row(
                    src_icon,
                    Text("☑", style="success") if device.is_selected else Text("☐", style="dim"),
                    Text("✓", style="green") if device.in_ai_scope else Text("-", style="dim"),
                    Text("✓", style="blue") if device.is_cached else Text("-", style="dim"),
                    Text(str(device.status), no_wrap=True),
                    Text(str(device.mac_address), no_wrap=True),
                    Text(str(device.customer), no_wrap=True),
                    Text(str(device.group), no_wrap=True),
                    Text(str(device.name), no_wrap=True),
                    Text(str(device.model), no_wrap=True),
                    Text(str(device.firmware), no_wrap=True),
                    Text(
                        str(device.ms_role),
                        no_wrap=True,
                        style="bold green"
                        if device.ms_role == "Master"
                        else "blue"
                        if device.ms_role == "Child"
                        else "dim"
                        if device.ms_role == "Standalone"
                        else "",
                    ),
                    Text(str(device.ms_parent_mac), no_wrap=True, style="dim"),
                    key=device.mac_address,
                )

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Executes Additive Omni-Filtering mechanics via cell selection.

        Resolves the column label to determine if a virtual tag or a physical
        attribute should be toggled in the universal search input. Supports
        additive chaining and token removal.

        Args:
            event (DataTable.CellSelected): The payload containing cursor coordinates.
        """
        table = self.query_one(DataTable)
        column_label = table.ordered_columns[event.coordinate.column].label.plain
        cell_value = event.value.plain if isinstance(event.value, Text) else str(event.value)
        if column_label == "Src":
            cell_value = cell_value.replace("☁️", "").replace("🏠", "").replace("🔄", "").strip()

        if column_label == "Sel":
            row_key, _ = table.coordinate_to_cell_key(event.coordinate)
            mac = row_key.value if row_key else None
            if not mac:
                return
            for device in self._fleet_data:
                if device.mac_address == mac:
                    device.is_selected = not device.is_selected
                    break
            self._apply_filter(self.query_one(Input).value)
            return

        if column_label == "AI":
            filter_token = "is:ai" if "✓" in cell_value else ""
        elif column_label == "Cache":
            filter_token = "is:cached" if "✓" in cell_value else ""
        else:
            filter_token = cell_value.replace("🟢", "").replace("🔴", "").replace("⚪", "").strip()

        if not filter_token:
            return

        search_input = self.query_one(Input)
        current_value = search_input.value
        tokens = current_value.split()

        if filter_token.lower() in [t.lower() for t in tokens]:
            new_tokens = [t for t in tokens if t.lower() != filter_token.lower()]
            new_value = " ".join(new_tokens)
            action_msg = f"Removed filter: {filter_token}"
        else:
            new_value = f"{current_value} {filter_token}".strip()
            action_msg = f"Added filter: {filter_token}"

        search_input.value = new_value
        self._apply_filter(new_value)
        self.notify(action_msg, severity="information")

    def action_toggle_ai(self) -> None:
        """Triggers the bulk AI Whitelist toggle for visible or selected devices."""
        table = self.query_one(DataTable)
        visible_macs = [row_key.value for row_key in table.rows.keys() if row_key.value]
        if not visible_macs:
            self.notify("No devices visible to toggle AI Scope", severity="warning")
            return

        selected_macs = [d.mac_address for d in self._fleet_data if d.mac_address in visible_macs and d.is_selected]
        target_macs = selected_macs if selected_macs else visible_macs
        target_desc = f"{len(target_macs)} SELECTED" if selected_macs else f"ALL {len(target_macs)} VISIBLE"

        self.app.push_screen(
            ConfirmModal(f"Toggle AI Scope for {target_desc} devices?"),
            lambda confirmed: self._on_ai_confirm(confirmed, target_macs),
        )

    def _on_ai_confirm(self, confirmed: bool, target_macs: list[str]) -> None:
        """Handles the AI toggle confirmation.

        Args:
            confirmed (bool): Whether the user confirmed the action.
            target_macs (List[str]): The list of MAC addresses to process.
        """
        if confirmed:
            target_set = set(target_macs)
            for device in self._fleet_data:
                if device.mac_address in target_set:
                    device.in_ai_scope = not device.in_ai_scope

            self._apply_filter(self.query_one(Input).value)
            self._save_tui_state()
            self.notify(f"AI Scope updated for {len(target_macs)} devices", severity="information")

    def action_deep_dive(self) -> None:
        """Triggers the bulk Deep-Dive for visible or selected devices.

        Filters out offline devices before prompting to prevent connection errors
        and TUI corruption from proxy HTML responses.
        """
        table = self.query_one(DataTable)
        visible_macs = [row_key.value for row_key in table.rows.keys() if row_key.value]
        if not visible_macs:
            self.notify("No devices visible for Deep Dive", severity="warning")
            return

        selected_macs = [d.mac_address for d in self._fleet_data if d.mac_address in visible_macs and d.is_selected]
        target_macs = selected_macs if selected_macs else visible_macs
        if len(target_macs) > 350:
            self.notify(
                f"Limit Exceeded: Cannot deep-dive {len(target_macs)} devices (Max 350).",
                severity="error",
            )
            return

        online_macs = [d.mac_address for d in self._fleet_data if d.mac_address in target_macs and "ONLINE" in d.status]

        if not online_macs:
            self.notify("No online devices selected for Deep Dive", severity="warning")
            return

        target_desc = f"{len(online_macs)} SELECTED" if selected_macs else f"ALL {len(online_macs)} VISIBLE"
        prompt_suffix = " (Skipping OFFLINE devices)" if len(online_macs) < len(target_macs) else ""

        self.app.push_screen(
            ConfirmModal(f"Fetch deep topology & cache {target_desc} devices?{prompt_suffix} This takes an API call per device."),
            lambda confirmed: self.run_worker(self._worker_deep_dive(online_macs)) if confirmed else None,
        )

    def action_toggle_select_all(self) -> None:
        """Toggles selection for all currently visible devices."""
        table = self.query_one(DataTable)
        visible_macs = set(row_key.value for row_key in table.rows.keys() if row_key.value)
        if not visible_macs:
            return

        visible_devices = [d for d in self._fleet_data if d.mac_address in visible_macs]
        all_selected = all(d.is_selected for d in visible_devices)

        for d in visible_devices:
            d.is_selected = not all_selected

        self._apply_filter(self.query_one(Input).value)
        self.notify(
            "Selected all visible" if not all_selected else "Deselected all visible",
            severity="information",
        )

    def action_local_scan(self) -> None:
        """Opens the local network discovery scanner modal."""
        self.app.push_screen(ScannerModal(), self._on_scan_confirm)

    def _on_scan_confirm(self, result: Optional[tuple[str, int]]) -> None:
        """Processes the result from the ScannerModal and launches the scan worker.

        Args:
            result (Optional[tuple[str, int]]): The (IP, count) tuple or None.
        """
        if result:
            self.run_worker(self._worker_local_scan(result[0], result[1]), exclusive=True)

    async def _worker_local_scan(self, start_ip: str, count: int) -> None:
        """Simulates/performs local network discovery for Xovis devices.

        Args:
            start_ip (str): The starting IP address for the scan.
            count (int): The number of hosts to probe.
        """
        table = self.query_one(DataTable)
        table.loading = True
        self.notify(f"Scanning {count} hosts starting from {start_ip}...", severity="information")

        await asyncio.sleep(1.5)

        try:
            from xovis.api.device.client import SmartDeviceClient

            discovery_master = None
            for dev in self._fleet_data:
                if dev.status == "🟢 ONLINE":
                    discovery_master = dev
                    break

            if not discovery_master:
                self.notify("No online Hub devices available to act as Discovery Proxy.", severity="warning")
                table.loading = False
                return

            async with SmartDeviceClient(
                mac_address=discovery_master.mac_address,
                host=discovery_master.ip_address,
                hub_client=self._hub_client,
                username=os.getenv("XOVIS_DEVICE_USERNAME", "admin"),
                password=os.getenv("XOVIS_DEVICE_PASSWORD", "pass"),
            ) as client:
                discovered_clients = await client.topology.scan(first_ip=start_ip, count=count)

                for d_client in discovered_clients:
                    try:
                        info = await d_client.info()
                        if not info:
                            continue

                        mac = info.get("mac_address", "00:00:00:00:00:00")
                        new_device = FleetDevice(
                            mac_address=mac,
                            status="🟢 LOCAL",
                            customer="Local Discovery",
                            group="LAN",
                            name=info.get("name", "New Local Sensor"),
                            model=info.get("type", "Unknown"),
                            firmware=info.get("fw_version", "Unknown"),
                            ms_role="Standalone",
                            ms_parent_mac="",
                            source="LAN",
                            ip_address=d_client._http_client.base_url.split("//")[-1].split(":")[0],
                        )
                        self._lan_devices[mac] = new_device
                    except Exception as e:
                        logging.error(f"Failed to probe discovered device: {e}")
                        continue

            self._rebuild_fleet_data_from_cache()
            table.loading = False
            self.notify(
                f"Local scan completed. Discovered {len(discovered_clients)} devices.",
                severity="success",
            )

        except Exception as e:
            table.loading = False
            self.notify(f"Local scan failed: {escape(str(e))}", severity="error")

    def _on_bucket_action(self, result: tuple[str, str]) -> None:
        """Processes the result from the BucketModal natively via the Cache Manager.

        Args:
            result (tuple[str, str]): A tuple of (action, bucket_name).
        """
        if not result or not self._hub_client:
            return

        action, name = result
        from pathlib import Path

        res_dir = Path("_local_ressources")
        if res_dir.exists() and os.access(res_dir, os.W_OK):
            file_path = str((res_dir / f"{name}.state.json").resolve())
        else:
            file_path = os.path.join(os.getcwd(), f"{name}.state.json")

        try:
            if action == "save":
                table = self.query_one(DataTable)
                visible_macs = {str(row_key.value).upper() for row_key in table.rows.keys() if row_key.value}
                logging.info(f"Bucket Save: {len(visible_macs)} devices visible in table.")

                is_filtered = bool(self.query_one(Input).value.strip())
                cache = self._hub_client.cache

                filtered_devices = [d for d in cache._state.devices if str(d.id.root if hasattr(d.id, "root") else d.id).upper() in visible_macs]

                if not is_filtered:
                    filtered_roles = {str(k).upper(): v for k, v in cache._state.topology_roles.items()}
                    filtered_parents = {str(k).upper(): [str(p).upper() for p in v] for k, v in cache._state.topology_parents.items()}
                else:
                    all_relevant_macs = set(visible_macs)

                    while True:
                        size_before = len(all_relevant_macs)

                        for k, v in cache._state.topology_parents.items():
                            if str(k).upper() in all_relevant_macs:
                                all_relevant_macs.update([str(p).upper() for p in v])

                        for k, v in cache._state.topology_parents.items():
                            if any(str(p).upper() in all_relevant_macs for p in v):
                                all_relevant_macs.add(str(k).upper())

                        if len(all_relevant_macs) == size_before:
                            break

                    filtered_parents = {
                        str(k).upper(): [str(p).upper() for p in v]
                        for k, v in cache._state.topology_parents.items()
                        if str(k).upper() in all_relevant_macs
                    }

                    filtered_roles = {str(k).upper(): v for k, v in cache._state.topology_roles.items() if str(k).upper() in all_relevant_macs}

                logging.info(f"Bucket Save: Exporting {len(filtered_roles)} roles and {len(filtered_parents)} parents.")

                custom_bucket = HubStateBucket(
                    devices=filtered_devices,
                    licenses=[],
                    topology_roles=filtered_roles,
                    topology_parents=filtered_parents,
                )

                cache.export_to_file(file_path, custom_bucket=custom_bucket)
                self.notify(f"State Bucket '{name}' saved to {file_path}.")

            elif action == "load":
                if not os.path.exists(file_path):
                    self.notify(f"State Bucket '{name}' not found.", severity="error")
                    return

                self._hub_client.cache.load_from_file(file_path, merge=True)
                self.query_one(Input).value = "is:cached"
                self._rebuild_fleet_data_from_cache()
                self.notify(f"State Bucket '{name}' loaded and merged.")

            elif action == "delete":
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.notify(f"State Bucket '{name}' deleted.")
                else:
                    self.notify(f"State Bucket '{name}' does not exist.", severity="warning")

        except Exception as e:
            self.notify(f"Bucket action '{action}' failed: {escape(str(e))}", severity="error")

    async def _worker_deep_dive(self, mac_addresses: list[str]) -> None:
        """Background worker to resolve true Layer 2.5 topology and hydrate cache.

        Hardened with an asyncio.Semaphore to prevent Xovis Hub API Gateway (WAF)
        HTTP 429 Rate Limiting, and enforces strict MAC address capitalization to
        maintain dictionary alignment between the Edge and the Cloud Hub.
        """
        self.notify(f"Starting Deep Dive for {len(mac_addresses)} devices...", severity="information")

        try:
            client = self._hub_client
            topology_map = {}
            master_set = set()
            failed_probes = set()

            concurrency_limit = asyncio.Semaphore(5)

            async def _probe_device(raw_mac: str) -> None:
                mac = raw_mac.upper()

                async with concurrency_limit:
                    host_ip = None
                    for dev in self._fleet_data:
                        if dev.mac_address.upper() == mac:
                            host_ip = dev.ip_address
                            break

                    try:
                        from xovis.api.device.client import SmartDeviceClient

                        async with SmartDeviceClient(
                            mac_address=mac,
                            host=host_ip,
                            hub_client=client,
                            username=os.getenv("XOVIS_DEVICE_USERNAME", "admin"),
                            password=os.getenv("XOVIS_DEVICE_PASSWORD", "pass"),
                        ) as device:
                            graph = await device.topology.get_ms_graph()

                            is_master = False
                            if (graph.master_mac and graph.master_mac.upper() == mac) or any(
                                c.mac_address and c.mac_address.upper() == mac and c.reference for c in graph.children
                            ):
                                is_master = True
                            elif not graph.master_mac and graph.children:
                                is_master = True
                            elif len(graph.children) > 1 and not any(c.reference for c in graph.children):
                                is_master = True

                            if is_master:
                                master_set.add(mac)

                            for child in graph.children:
                                child_mac = child.mac_address.upper() if child.mac_address else None
                                if child_mac and child_mac != mac:
                                    if child_mac not in topology_map:
                                        topology_map[child_mac] = []
                                    if mac not in topology_map[child_mac]:
                                        topology_map[child_mac].append(mac)

                        await asyncio.sleep(1.0)

                    except Exception as probe_error:
                        logging.warning(f"Failed to probe {mac}: {probe_error}", exc_info=True)
                        failed_probes.add(mac)

            tasks = [_probe_device(mac) for mac in mac_addresses]
            await asyncio.gather(*tasks)

            client.cache._state.topology_roles.update({m.upper(): "Master" for m in master_set})

            for child_mac, parents in topology_map.items():
                client.cache._state.topology_roles[child_mac.upper()] = "Child"
                if child_mac.upper() not in client.cache._state.topology_parents:
                    client.cache._state.topology_parents[child_mac.upper()] = []
                for p in parents:
                    if p.upper() not in client.cache._state.topology_parents[child_mac.upper()]:
                        client.cache._state.topology_parents[child_mac.upper()].append(p.upper())

            probed_macs = {m.upper() for m in mac_addresses}
            standalone_updates = {}
            for mac in probed_macs:
                if mac not in master_set and mac not in topology_map and mac not in failed_probes:
                    standalone_updates[mac] = "Standalone"

            client.cache._state.topology_roles.update(standalone_updates)

            self._rebuild_fleet_data_from_cache()

        except Exception as e:
            self.notify(f"Deep Dive failed: {e}", severity="error")
        finally:
            self._save_tui_state()
            self.notify("Deep Dive complete", severity="information")
