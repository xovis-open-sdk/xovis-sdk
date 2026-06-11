"""
Xovis SDK - TUI & Setup Orchestrator

This module provides the guided terminal user interfaces for configuring the SDK
and managing Xovis fleets. It uses Textual for the rich management dashboard
and Questionary for the guided setup wizard.
"""

import asyncio
import os
from pathlib import Path

import questionary
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from xovis.api.device.client import DeviceClient


class SetupWizard:
    """
    Guided CLI wizard for SDK initialization and environment configuration.
    """

    def __init__(self, env_path: str = ".env"):
        """
        Initializes the setup wizard.

        Args:
            env_path (str): The file path where credentials will be stored.
                Defaults to '.env'.
        """
        self.env_path = Path(env_path).resolve()

    def run(self):
        """Executes the guided setup flow."""
        print("\n\033[1m  Xovis SDK Setup Wizard\033[0m")
        print("  " + "─" * 30)

        # 1. Hub Configuration
        setup_hub = questionary.confirm("Configure Xovis HUB Cloud credentials?").ask()
        hub_vars = {}
        if setup_hub:
            hub_vars["XOVIS_HUB_CLIENT_ID"] = questionary.text("HUB Client ID:", default=os.getenv("XOVIS_HUB_CLIENT_ID", "")).ask()
            hub_vars["XOVIS_HUB_CLIENT_SECRET"] = questionary.password("HUB Client Secret:", default=os.getenv("XOVIS_HUB_CLIENT_SECRET", "")).ask()

        # 2. Local Device Defaults
        setup_device = questionary.confirm("Configure default device credentials?").ask()
        device_vars = {}
        if setup_device:
            device_vars["XOVIS_DEVICE_USER"] = questionary.text("Default Device Username:", default=os.getenv("XOVIS_DEVICE_USER", "admin")).ask()
            device_vars["XOVIS_DEVICE_PASS"] = questionary.password("Default Device Password:", default=os.getenv("XOVIS_DEVICE_PASS", "pass")).ask()

        # 3. Hardware Warmup
        if setup_device:
            warmup_host = questionary.text("Enter a Device IP for Hardware Warmup (fetch schemas):", default=os.getenv("XOVIS_DEVICE_IP", "")).ask()
            if warmup_host:
                from xovis.api.device.sync import HardwareSyncer

                syncer = HardwareSyncer(warmup_host, device_vars["XOVIS_DEVICE_USER"], device_vars["XOVIS_DEVICE_PASS"])
                print(f"\n\033[1mRunning Hardware Warmup for {warmup_host}...\033[0m")
                success = asyncio.run(syncer.warmup())
                if success:
                    print("\033[92m[SUCCESS]\033[0m Hardware warmup completed.")
                else:
                    print("\033[91m[FAILED]\033[0m Hardware warmup failed.")

        # 4. HUB Warmup
        if setup_hub:
            if questionary.confirm("Perform HUB Cloud Warmup (fetch cloud schemas)?").ask():
                from xovis.api.hub.sync import HubSyncer

                syncer = HubSyncer(client_id=hub_vars["XOVIS_HUB_CLIENT_ID"], client_secret=hub_vars["XOVIS_HUB_CLIENT_SECRET"])
                print("\n\033[1mRunning Xovis HUB Warmup...\033[0m")
                success = asyncio.run(syncer.warmup())
                if success:
                    print("\033[92m[SUCCESS]\033[0m HUB warmup completed.")
                else:
                    print("\033[91m[FAILED]\033[0m HUB warmup failed.")

        # 5. Persistence
        all_vars = {**hub_vars, **device_vars}
        if all_vars:
            if questionary.confirm(f"Save credentials to {self.env_path.name}?").ask():
                self._save_env(all_vars)
                print(f"\n\033[92m[SUCCESS]\033[0m Credentials saved to {self.env_path.name}")

        print("\n\033[1mSetup complete!\033[0m You can now use 'xovis probe' or 'xovis mcp'.\n")

    def _save_env(self, variables: dict):
        """Writes variables to the .env file."""
        lines = []
        if self.env_path.exists():
            lines = self.env_path.read_text().splitlines()

        for key, value in variables.items():
            # Replace existing or append
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={value}")

        self.env_path.write_text("\n".join(lines) + "\n")


class DeviceItem(ListItem):
    """A list item representing a Xovis device."""

    has_transmission = reactive(False)

    def __init__(self, name: str, ip: str, mac: str):
        """
        Initializes the device list item.

        Args:
            name (str): Human-readable device name.
            ip (str): Network IP address of the device.
            mac (str): Physical MAC address of the device.
        """
        super().__init__()
        self.device_name = name
        self.device_ip = ip
        self.device_mac = mac

    def compose(self) -> ComposeResult:
        """
        Hydrates the list item layout.

        Yields:
            ComposeResult: The formatted label widget.
        """
        tx_marker = "[green]●[/green] " if self.has_transmission else ""
        yield Label(
            f"{tx_marker}[b]{self.device_name}[/b] ({self.device_ip}) - {self.device_mac}",
            id="item-label",
        )

    def watch_has_transmission(self, has_tx: bool) -> None:
        """Update the label when transmission status changes."""
        try:
            label = self.query_one("#item-label", Label)
            tx_marker = "[green]●[/green] " if has_tx else ""
            label.update(f"{tx_marker}[b]{self.device_name}[/b] ({self.device_ip}) - {self.device_mac}")
        except Exception:
            # Widget might not be mounted yet
            pass


class XovisTUI(App):
    """
    Main TUI application for Xovis Fleet Management.
    """

    TITLE = "Xovis SDK Mission Control"
    CSS = """
    Screen {
        background: #1e1e1e;
    }
    #main-container {
        padding: 1;
    }
    #device-list {
        width: 40%;
        border: solid green;
        height: 100%;
    }
    #detail-panel {
        width: 60%;
        border: solid blue;
        padding: 1;
    }
    .header-text {
        text-align: center;
        background: #333;
        color: white;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh Fleet"),
        ("t", "setup_transmission", "Setup Transmission"),
        ("x", "remove_transmission", "Remove Transmission"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal():
                with Vertical(id="device-list"):
                    yield Label("DEVICES", classes="header-text")
                    yield ListView(id="list-view")
                with Vertical(id="detail-panel"):
                    yield Label("DEVICE DETAILS", classes="header-text")
                    yield Static("Select a device to view details.", id="details")
        yield Footer()

    async def on_mount(self) -> None:
        """Initial data load."""
        await self.action_refresh()

    async def action_refresh(self) -> None:
        """Refreshes the device list from HUB or local discovery."""
        list_view = self.query_one("#list-view", ListView)
        list_view.clear()

        # In a real scenario, we would use HubClient here.
        # For now, we add the known test sensor and some mock data.
        await list_view.append(DeviceItem("Test Sensor", "192.168.178.38", "00:07:32:AB:8C:E2"))
        await list_view.append(DeviceItem("Lobby North", "10.0.0.15", "00:07:32:FF:11:22"))
        await list_view.append(DeviceItem("Supportroom", "10.0.0.22", "00:07:32:AA:BB:CC"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handles device selection."""
        item = event.item
        if isinstance(item, DeviceItem):
            details = self.query_one("#details", Static)
            details.update(
                f"[b]Name:[/b] {item.device_name}\n"
                f"[b]IP:[/b]   {item.device_ip}\n"
                f"[b]MAC:[/b]  {item.device_mac}\n\n"
                f"[yellow]Probing live status...[/yellow]"
            )
            # Trigger async probe
            asyncio.create_task(self._trigger_probe(item))

    async def _delayed_refresh(self, item: DeviceItem, delay: float = 3.0) -> None:
        """Refreshes the UI after a delay to allow the user to read success messages."""
        await asyncio.sleep(delay)
        await self._trigger_probe(item)

    async def _trigger_probe(self, item: DeviceItem) -> None:
        """Asynchronously probes the device and updates the UI."""
        details = self.query_one("#details", Static)
        try:
            # We use a context manager to ensure the client is closed
            async with DeviceClient(item.device_ip, "admin", "pass", timeout=5.0, max_retries=1) as client:
                wifi = await client.has_wifi
                analytics = await client.has_analytics
                itxpt = await client.has_itxpt

                # Fetch more details as requested
                info = await client.system.get_info()
                multisensors = await client.system.get_multisensors()

                # Determine parent/child status
                # If it has multisensors, it's part of a cluster.
                # Usually if 'is_master' is true in any cluster, it's a parent.
                is_child = len(multisensors) > 0
                role = "Child" if is_child else "Standalone/Parent"

                # Tilt/Shift and Tracker Version
                # These are usually in info.hardware if using models, or direct if raw dict
                # Based on SystemManager.get_info returning a model
                tilt = getattr(info, "tilt", "N/A")
                shift = getattr(info, "shift", "N/A")
                tracker_version = getattr(info, "tracker_version", "N/A")
                device_type = getattr(info, "type", "Unknown")

                # Fetch Geometries and Logics
                geometries = []
                logics = []

                # Fetch DataPush connections and agents
                connections = []
                agents = []

                if not client.is_spider:
                    try:
                        geoms_resp = await client.singlesensor.scene.get_all_geometries()
                        # Some models have .geometries list, others are root lists
                        if hasattr(geoms_resp, "geometries"):
                            geometries = geoms_resp.geometries
                        elif isinstance(geoms_resp, list):
                            geometries = geoms_resp
                        else:
                            # Fallback if it's a model that is iterable
                            geometries = list(geoms_resp) if hasattr(geoms_resp, "__iter__") else []
                    except Exception:
                        pass

                    try:
                        conn_coll = await client.singlesensor.datapush.get_all_connections()
                        connections = conn_coll.connections or []
                        agent_coll = await client.singlesensor.datapush.get_all_agents()
                        agents = agent_coll.agents or []
                    except Exception:
                        pass

                if analytics:
                    try:
                        logics_resp = await client.singlesensor.analytics.get_all_logics()
                        if hasattr(logics_resp, "logics"):
                            logics = logics_resp.logics
                        elif isinstance(logics_resp, list):
                            logics = logics_resp
                        else:
                            logics = list(logics_resp) if hasattr(logics_resp, "__iter__") else []
                    except Exception:
                        pass

                content = (
                    f"[b]Name:[/b] {item.device_name}\n"
                    f"[b]IP:[/b]   {item.device_ip}\n"
                    f"[b]MAC:[/b]  {item.device_mac}\n\n"
                    f"[b]Status:[/b] [green]Online[/green] | [b]Role:[/b] {role}\n"
                    f"[b]Type:[/b] {device_type} | [b]Firmware:[/b] {client.fw_version}\n"
                    f"[b]Tracker:[/b] {tracker_version} | [b]Tilt/Shift:[/b] {tilt}/{shift}\n\n"
                    f"[b]Capabilities:[/b]\n"
                    f"  - WiFi/BT:    {'[green]YES[/green]' if wifi else '[red]NO[/red]'}\n"
                    f"  - Analytics:  {'[green]YES[/green]' if analytics else '[red]NO[/red]'}\n"
                    f"  - ITxPT:      {'[green]YES[/green]' if itxpt else '[red]NO[/red]'}\n\n"
                    f"[b]Scene:[/b] {len(geometries)} Geometries\n"
                    f"[b]Analytics:[/b] {len(logics)} Logics\n\n"
                    f"[b]DataPush:[/b] {len(connections)} Connections, {len(agents)} Agents\n"
                )

                if connections:
                    content += "\n[b]Connections:[/b]\n"
                    for c in connections:
                        c_root = c.root
                        content += f"  - {c_root.name} ({c_root.protocol})\n"

                if agents:
                    content += "\n[b]Agents:[/b]\n"
                    for a in agents:
                        content += f"  - {a.name} ({a.type}) {'[green]Enabled[/green]' if a.enabled else '[red]Disabled[/red]'}\n"

                has_sdk_tx = any(getattr(c.root, "name", "") == "SDK-Transmission-Check" for c in connections)

                # Update item marker via reactive property
                item.has_transmission = has_sdk_tx

                if has_sdk_tx:
                    content += "\n[white on green] [b]SDK TRANSMISSION ACTIVE[/b] [/white on green]\n"

                prompt = "[white on blue] Press 'T' to Setup Transmission DataPush [/white on blue]"
                if has_sdk_tx:
                    prompt = "[white on red] Press 'X' to Remove SDK Transmission DataPush [/white on red]"

                content += f"\n\n{prompt}"
                details.update(content)
                self.selected_device = item
        except Exception as e:
            details.update(
                f"[b]Name:[/b] {item.device_name}\n"
                f"[b]IP:[/b]   {item.device_ip}\n"
                f"[b]MAC:[/b]  {item.device_mac}\n\n"
                f"[b]Status:[/b] [red]Offline / Connection Error[/red]\n"
                f"[dim]Error: {str(e)}[/dim]"
            )

    async def action_setup_transmission(self) -> None:
        """Sets up a DataPush configuration for transmission checking."""
        if not hasattr(self, "selected_device") or not self.selected_device:
            return

        item = self.selected_device
        details = self.query_one("#details", Static)
        details.update(f"[yellow]Setting up Transmission DataPush for {item.device_ip}...[/yellow]")

        try:
            import socket

            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            async with DeviceClient(item.device_ip, "admin", "pass") as client:
                models = client.models

                # 1. Create Connection
                # Check if it exists
                connection_collection = await client.singlesensor.datapush.get_all_connections()
                connections = connection_collection.connections or []
                conn_name = "SDK-Transmission-Check"
                conn_id = None
                for c in connections:
                    # ConnectionConfig is a RootModel
                    if getattr(c.root, "name", "") == conn_name:
                        conn_id = c.root.id
                        break

                if not conn_id:
                    # Create new TCP connection
                    config = models.Config5(
                        uri=f"tcp://{local_ip}",
                        port=9000,
                        mode=models.Mode.CLIENT,
                        connection_timeout_s=5,
                    )
                    new_conn = models.ConnectionConfigTcp(name=conn_name, protocol=models.Protocol4.TCP, config=config)
                    # DataPushManager expects ConnectionConfig RootModel
                    await client.singlesensor.datapush.create_connection(models.ConnectionConfig(new_conn))
                    # We might need to fetch all again to get the ID if not in resp
                    connection_collection = await client.singlesensor.datapush.get_all_connections()
                    connections = connection_collection.connections or []
                    for c in connections:
                        if getattr(c.root, "name", "") == conn_name:
                            conn_id = c.root.id
                            break

                # Test Connection
                if conn_id:
                    details.update(f"[yellow]Testing Connection {conn_name}...[/yellow]")

                    # Start a temporary listener to satisfy the sensor's connection test
                    # If port 9000 is already in use, we assume another process (like transmission-check)
                    # is already listening, so we just proceed with the test.
                    test_server = None
                    try:
                        test_server = await asyncio.start_server(lambda r, w: w.close(), "0.0.0.0", 9000)  # nosec B104
                    except OSError as e:
                        if e.errno == 10048 or "10048" in str(e):
                            details.update("[yellow]Port 9000 busy, assuming monitor is already running.[/yellow]")
                        else:
                            raise

                    try:
                        if test_server:
                            async with test_server:
                                test_res = await client.singlesensor.datapush.test_connection(conn_id)
                        else:
                            test_res = await client.singlesensor.datapush.test_connection(conn_id)

                        test_data = test_res.get("connection_test", {}) if isinstance(test_res, dict) else getattr(test_res, "connection_test", {})
                        status = test_data.get("status", "UNKNOWN") if isinstance(test_data, dict) else getattr(test_data, "status", "UNKNOWN")
                        if status != "OK":
                            info = (
                                test_data.get("server_response", {}).get("info", "Unknown error") if isinstance(test_data, dict) else "Check sensor"
                            )
                            details.update(
                                f"[red]Connection Test Failed: {status} ({info})[/red]\n"
                                f"Ensure your firewall allows incoming TCP on port 9000.\n"
                                f"[yellow]Retrying setup in 5 seconds...[/yellow]"
                            )
                            await asyncio.sleep(5)
                    except Exception as e:
                        details.update(f"[red]Connection Test Error:[/red] {str(e)}")
                        await asyncio.sleep(3)

                # 2. Create Agent
                agent_collection = await client.singlesensor.datapush.get_all_agents()
                agents = agent_collection.agents or []
                agent_name = "SDK-Live-Stream"
                agent_exists = False
                for a in agents:
                    if a.name == agent_name:
                        agent_exists = True
                        break

                if not agent_exists:
                    agent_config = models.AgentConfig(
                        name=agent_name,
                        type=models.AgentTypes.LIVE_DATA,
                        enabled=True,
                        connection=conn_id,
                        config=models.Config(scheduler=models.Scheduler(type=models.SchedulerTypes.IMMEDIATE)),
                    )
                    await client.singlesensor.datapush.create_agent(agent_config)

            details.update(
                f"[green]Successfully configured DataPush![/green]\n"
                f"Connection: {conn_name} -> {local_ip} port 9000\n"
                f"Agent: {agent_name} (LIVE_DATA)\n\n"
                f"You can now run [b]xovis transmission-check[/b] to see live data."
            )
            # Re-trigger probe to refresh UI after a short delay
            asyncio.create_task(self._delayed_refresh(item))
        except Exception as e:
            details.update(f"[red]Failed to setup DataPush:[/red]\n{str(e)}")

    async def action_remove_transmission(self) -> None:
        """Removes the SDK-created DataPush configuration."""
        if not hasattr(self, "selected_device") or not self.selected_device:
            return

        item = self.selected_device
        details = self.query_one("#details", Static)
        details.update(f"[yellow]Removing Transmission DataPush for {item.device_ip}...[/yellow]")

        try:
            async with DeviceClient(item.device_ip, "admin", "pass") as client:
                # 1. Remove Agent
                agent_collection = await client.singlesensor.datapush.get_all_agents()
                agents = agent_collection.agents or []
                for a in agents:
                    if a.name == "SDK-Live-Stream":
                        await client.singlesensor.datapush.delete_agent(a.id)
                        break

                # 2. Remove Connection
                connection_collection = await client.singlesensor.datapush.get_all_connections()
                connections = connection_collection.connections or []
                for c in connections:
                    if getattr(c.root, "name", "") == "SDK-Transmission-Check":
                        await client.singlesensor.datapush.delete_connection(c.root.id)
                        break

            details.update(f"[green]Successfully removed SDK DataPush resources from {item.device_ip}.[/green]")
            # Re-trigger probe to refresh UI after a short delay
            asyncio.create_task(self._delayed_refresh(item))
        except Exception as e:
            details.update(f"[red]Failed to remove DataPush:[/red]\n{str(e)}")
