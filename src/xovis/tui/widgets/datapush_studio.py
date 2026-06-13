"""
Xovis SDK - Xovis Open SDK Datapush Studio Widget

Provides a real-time telemetry dashboard for monitoring Xovis DataPlane
throughput. Binds directly to the XovisTCPServer and updates metrics via
Textual reactivity.
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from rich.markup import escape

if TYPE_CHECKING:
    from textual.widgets import Select

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Input, Label, Sparkline, Static

from xovis.api.device.client import DeviceClient
from xovis.models.device import DataPushAgent, DataPushConnection


class MetricSink:
    """
    A custom XovisSink that updates Textual reactive properties.

    Acts as the bridge between the high-frequency Data Plane and the
    TUI lifecycle.
    """

    def __init__(self, widget: "DatapushStudio", agent_type: str = "LIVE_DATA", debug: bool = False):
        """
        Initializes the metric sink.

        Args:
            widget (DatapushStudio): The parent widget to update.
            agent_type (str): The type of agent being monitored.
            debug (bool): If True, logs raw frames to 'xovis_studio_debug.log'.
        """
        self.widget = widget
        self.agent_type = agent_type
        self.debug = debug
        self._last_push_time: float = time.time()

        if self.debug:
            try:
                with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"--- MetricSink initialized for {agent_type} ---\n")
            except Exception:
                pass

    async def on_frame(self, payload: dict | list) -> None:
        """
        Updates frame count and throughput metrics.

        Args:
            payload (dict | list): The parsed telemetry payload.
        """
        try:
            import json

            self.widget.total_bytes += len(json.dumps(payload))
            self.widget.last_frame_time = time.time()

            # Normalize to a list of frames
            frames_to_process = payload if isinstance(payload, list) else [payload]

            # Use current widget agent_type to prevent stale parsing logic
            active_type = self.widget.agent_type

            for frame in frames_to_process:
                self.widget.frame_count += 1

                # Extract Package Sequence ID
                pkg_info = frame.get("package_info", {})
                if pkg_info:
                    self.widget.seq_id = pkg_info.get("id", 0)
                elif frame.get("logics_data"):
                    # Handle logics wrapping format
                    self.widget.seq_id = frame.get("logics_data", {}).get("package_info", {}).get("id", 0)
                elif frame.get("status_data"):
                    # Handle status wrapping format
                    self.widget.seq_id = frame.get("status_data", {}).get("package_info", {}).get("id", 0)

                if active_type == "LIVE_DATA":
                    live_data = frame.get("live_data", {})
                    sub_frames = live_data.get("frames", [])
                    persons = 0
                    groups = 0

                    # Copy dict to trigger reactive watcher on update
                    evt_dict = self.widget.events_breakdown.copy()

                    for sf in sub_frames:
                        tracks = sf.get("tracked_objects", [])
                        for t in tracks:
                            if t.get("type") == "PERSON":
                                persons += 1
                            elif t.get("type") == "GROUP":
                                groups += 1

                        for evt in sf.get("events", []):
                            evt_type = evt.get("type", "UNKNOWN")
                            # Shorten LINE_CROSS_FORWARD to LCF
                            short = "".join([w[0] for w in evt_type.split("_")])
                            evt_dict[short] = evt_dict.get(short, 0) + 1

                    self.widget.current_tracks_person = persons
                    self.widget.current_tracks_group = groups
                    self.widget.events_breakdown = evt_dict

                elif active_type == "LOGICS":
                    logics_data = frame.get("logics_data", {})
                    logics = logics_data.get("logics", [])
                    if logics:
                        self.widget.active_logics = len(logics)

                        fw_count = 0
                        bw_count = 0
                        visit_count = 0
                        dwell_time_avg = 0.0
                        dwell_samples = 0
                        samples_recv = 0
                        samples_exp = 0

                        for logic in logics:
                            for record in logic.get("records", []):
                                samples_recv += record.get("samples", 0)
                                samples_exp += record.get("samples_expected", 0)
                                for count_obj in record.get("counts", []):
                                    name = count_obj.get("name")
                                    val = count_obj.get("value", 0)
                                    if name == "fw":
                                        fw_count += val
                                    elif name == "bw":
                                        bw_count += val
                                    elif name == "visits":
                                        visit_count += val
                                    elif name == "dwell_time":
                                        dwell_time_avg += float(val)
                                        dwell_samples += 1

                        self.widget.logics_fw = fw_count
                        self.widget.logics_bw = bw_count
                        self.widget.logics_visits = visit_count
                        self.widget.logics_dwell = dwell_time_avg / dwell_samples if dwell_samples > 0 else 0.0
                        self.widget.logic_samples = (samples_recv, samples_exp)

                        now = time.time()
                        self.widget.push_interval = now - self._last_push_time
                        self._last_push_time = now

                elif active_type == "STATUS":
                    status_data = frame.get("status_data", {})
                    states = status_data.get("states", {})

                    # 1. Device Info (Firmware)
                    device = states.get("device", {})
                    fw = device.get("info", {}).get("fw_version", "N/A")
                    self.widget.sensor_fw = str(fw)

                    # 2. Device State (Temp & Uptime)
                    details = device.get("state", {}).get("details", {})
                    temps = details.get("temperatures", {})
                    self.widget.sensor_temp = str(temps.get("die", "N/A"))

                    uptime = details.get("uptime_sec", 0)
                    self.widget.sensor_uptime = f"{(uptime / 3600):.1f}"

                    # 3. Network State (Dropped Packets)
                    network = states.get("network", {}).get("state", {}).get("details", {}).get("link", {})
                    self.widget.dropped_pkts = network.get("rx_dropped", 0)

                elif str(active_type) == "RECORDING":
                    # Recording pushes might be binary or JSON validation_recording
                    recording_data = frame.get("recording_data") or frame.get("validation_recording")
                    if recording_data:
                        # If it's a dict, we might extract more
                        if isinstance(recording_data, dict):
                            self.widget.sensor_fw = str(recording_data.get("version", "N/A"))
                        # We just update frame count and bytes (already done above)
                        # We don't have specific fields for recording yet, but we show seq_id if available
                        pkg_info = frame.get("package_info", {})
                        if pkg_info:
                            self.widget.seq_id = pkg_info.get("id", 0)

            if self.debug:
                with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload) + "\n")

        except Exception as e:
            logger = logging.getLogger("xovis-sdk")
            logger.error(f"MetricSink.on_frame error: {e}")

    async def on_events(self, events: list) -> None:
        self.widget.total_events += len(events)


class StatCard(Static):
    """A reactive widget for displaying individual stream performance metrics."""

    DEFAULT_CSS = """
    StatCard {
        background: $boost;
        border: panel $primary;
        padding: 0 1;
        width: 1fr;
        height: 5;
        content-align: center middle;
    }
    StatCard .stat-label {
        width: 100%;
        text-align: center;
        color: $text-muted;
        text-style: bold;
    }
    StatCard .stat-value {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $success;
    }
    """

    def __init__(
        self,
        label: str,
        value: str = "0",
        unit: str = "",
        id: Optional[str] = None,
        display: bool = True,
    ):
        super().__init__(id=id)
        self.label = label
        self.value_text = value
        self.unit = unit
        self.display = display

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="stat-label")
        yield Label(f"{self.value_text} [dim]{self.unit}[/dim]", id=f"{self.id}-value", classes="stat-value")

    def update_value(self, value: str):
        try:
            val_label = self.query_one(f"#{self.id}-value", Label)
            val_label.update(f"{value} [dim]{self.unit}[/dim]")
        except Exception:
            pass

    def update_label(self, label: str):
        try:
            self.query_one(".stat-label", Label).update(label)
        except Exception:
            pass


class DatapushStudio(Static):
    """
    Real-time telemetry and throughput dashboard.

    Binds a XovisTCPServer to the TUI. When active (F5), it listens for
    incoming sensor data and visualizes throughput via a Sparkline.
    """

    frame_count = reactive(0)
    total_bytes = reactive(0)
    fps = reactive(0.0)
    is_active = reactive(False)
    protocol = reactive("TCP")
    agent_type = reactive("LIVE_DATA")
    provisioning_status = reactive("Idle")
    throughput = reactive(0.0)
    throughput_avg = reactive(0.0)
    throughput_max = reactive(0.0)
    throughput_min = reactive(-1.0)
    total_events = reactive(0)
    seq_id = reactive(0)

    # New Dynamic KPI Properties
    current_tracks_person = reactive(0)
    current_tracks_group = reactive(0)
    active_logics = reactive(0)
    # Logic KPIs
    logics_fw = reactive(0)
    logics_bw = reactive(0)
    logics_visits = reactive(0)
    logics_dwell = reactive(0.0)
    push_interval = reactive(0.0)
    sensor_temp = reactive("N/A")
    sensor_uptime = reactive("0.0")
    dropped_pkts = reactive(0)
    events_breakdown = reactive({})
    logic_samples = reactive((0, 0))  # (received, expected)
    sensor_fw = reactive("N/A")

    BINDINGS = [
        ("f5", "toggle_server", "Start/Stop Server"),
        ("q", "app.quit", "Quit"),
    ]

    CSS = """
    DatapushStudio #studio-container {
        height: 1fr;
        border: double $accent;
        padding: 1;
    }
    DatapushStudio #studio-header {
        background: $accent;
        color: $text;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    DatapushStudio #config-panel {
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
        height: 16; /* Increased for 3 rows and Select expansion */
    }
    DatapushStudio .form-row {
        height: 3;
        margin-bottom: 1;
    }
    DatapushStudio .form-group {
        width: 1fr;
        height: auto;
        margin-right: 2;
    }
    DatapushStudio .form-label {
        color: $text-muted;
        text-style: bold;
    }
    DatapushStudio #metrics-panel {
        border: solid $success;
        padding: 0;
        height: auto;
    }
    DatapushStudio #metric-container {
        height: auto;
        padding: 0;
    }
    DatapushStudio .card-row {
        height: 5;
        margin-bottom: 0;
    }
    DatapushStudio #row-live {
        display: block;
    }
    DatapushStudio #row-logics {
        display: none;
    }
    DatapushStudio #row-status {
        display: none;
    }
    DatapushStudio #throughput-sparkline {
        height: 3;
        color: $success;
        margin-top: 1;
    }
    DatapushStudio #status-hint {
        text-align: center;
        margin-top: 1;
    }
    DatapushStudio #provision-status {
        text-align: center;
        color: $warning;
        text-style: italic;
    }
    DatapushStudio.server-active {
        border: double $success;
    }
    """

    def __init__(
        self,
        device_id: str = "",
        initial_port: str = "9000",
        initial_protocol: str = "TCP",
        initial_agent_type: str = "LIVE_DATA",
        initial_password: str = "pass",
        **kwargs,
    ):
        """Initializes the Datapush Studio.

        Args:
            device_id (str): The IP or MAC of the target sensor.
            initial_port (str): Default port to use.
            initial_protocol (str): Default protocol to use.
            initial_agent_type (str): Default agent type to use.
            initial_password (str): Default password to use.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.device_id = device_id
        self.initial_port = initial_port
        self.initial_protocol = initial_protocol
        self.initial_agent_type = initial_agent_type
        self.initial_password = initial_password
        self.server: Optional[Any] = None
        self._server_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self.last_frame_time: float = 0.0
        self._throughput_history: list[float] = []
        self._is_unmounting: bool = False

    def compose(self) -> ComposeResult:
        """Compose the Datapush Studio layout."""
        import socket

        from textual.widgets import Select

        # Discover local network interfaces dynamically
        local_ips = [("Auto-Discover (Default)", "AUTO")]
        try:
            _, _, ip_list = socket.gethostbyname_ex(socket.gethostname())
            for ip in ip_list:
                local_ips.append((f"{ip} (Local NIC)", ip))
        except Exception:
            pass

        if len(local_ips) == 1:
            local_ips.append(("127.0.0.1 (Loopback)", "127.0.0.1"))

        with Vertical(id="studio-container"):
            yield Label("[b]XOVIS OPEN SDK DATAPUSH STUDIO[/b]", id="studio-header")

            with Container(id="config-panel"):
                # ROW 1
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-group"):
                        yield Label("Protocol", classes="form-label")
                        yield Select(
                            options=[("TCP", "TCP"), ("UDP", "UDP"), ("HTTP", "HTTP")],
                            value=self.initial_protocol,
                            id="select-protocol",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Agent Type", classes="form-label")
                        yield Select(
                            options=[
                                ("LIVE_DATA", "LIVE_DATA"),
                                ("LOGICS", "LOGICS"),
                                ("STATUS", "STATUS"),
                                ("RECORDING", "RECORDING"),
                            ],
                            value=self.initial_agent_type,
                            id="select-agent-type",
                        )
                    with Vertical(classes="form-group"):
                        yield Label("Context", classes="form-label")
                        yield Select(
                            options=[
                                ("Singlesensor", "Singlesensor"),
                                ("Multisensor", "Multisensor"),
                            ],
                            value="Singlesensor",
                            id="select-context",
                        )

                # ROW 2
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-group"):
                        yield Label("Sensor IP (Blank = Listen)", classes="form-label")
                        yield Input(placeholder="e.g., 10.0.0.50", id="input-host", value=self.device_id)
                    with Vertical(classes="form-group"):
                        yield Label("Listen Port", classes="form-label")
                        yield Input(placeholder="e.g., 9000", id="input-port", value=str(self.initial_port))
                    with Vertical(classes="form-group"):
                        yield Label("Callback Interface", classes="form-label")
                        yield Select(
                            options=local_ips,
                            value="AUTO",
                            id="select-callback",
                        )

                # ROW 3
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-group"):
                        yield Label("Sensor Password", classes="form-label")
                        yield Input(
                            placeholder="Password",
                            id="input-pass",
                            value=self.initial_password,
                            password=True,
                        )
                    with Vertical(classes="form-group"):
                        yield Label("DataPush Agent Name", classes="form-label")
                        yield Input(placeholder="Agent Name", id="input-name", value="OpenSDK-Studio")
                    with Vertical(classes="form-group"):
                        from textual.widgets import Checkbox

                        yield Label("Studio Options", classes="form-label")
                        with Horizontal():
                            yield Checkbox("Debug Log", id="check-debug", value=False)
                            yield Checkbox("Keep Provisioning on Exit", id="check-keep", value=False)

            with Container(id="metrics-panel"):
                with Vertical(id="metric-container"):
                    # ROW 1 (Always Visible)
                    with Horizontal(classes="card-row"):
                        yield StatCard("FPS", "0.0", "", id="card-fps")
                        yield StatCard("THROUGHPUT", "0.0", "KB/s", id="card-throughput")
                        yield StatCard("AVG | MIN | MAX", "0.0 | 0.0 | 0.0", "", id="card-analytics")
                        yield StatCard("SEQ ID", "0", "pkg", id="card-seq")
                        yield StatCard("PACKETS", "0", "pkts", id="card-frames")

                    # ROW 2 (Dynamic Mode Rows)
                    with Horizontal(classes="card-row", id="row-live"):
                        yield StatCard("PERSON TRACKS", "0", "objs", id="card-persons")
                        yield StatCard("GROUP TRACKS", "0", "objs", id="card-groups")
                        yield StatCard("EVENTS", "None", "", id="card-events")
                        yield StatCard("PUSH INTERVAL", "0.0", "s", id="card-interval")

                    with Horizontal(classes="card-row", id="row-logics"):
                        yield StatCard("FORWARD (FW)", "0", "crosses", id="card-fw")
                        yield StatCard("BACKWARD (BW)", "0", "crosses", id="card-bw")
                        yield StatCard("VISITS (ZONE)", "0", "objs", id="card-visits")
                        yield StatCard("AVG DWELL", "0.0", "s", id="card-dwell")
                        yield StatCard("ACTIVE LOGICS", "0", "zones", id="card-active-logics")
                        yield StatCard("SAMPLES", "0/0", "smpl", id="card-samples")

                    with Horizontal(classes="card-row", id="row-status"):
                        yield StatCard("TEMPERATURE", "N/A", "C", id="card-temp")
                        yield StatCard("UPTIME", "0.0", "h", id="card-uptime")
                        yield StatCard("DROPPED PKTS", "0", "pkts", id="card-dropped")
                        yield StatCard("FIRMWARE", "N/A", "fw", id="card-firmware")

                    # ROW 3
                    yield Sparkline(data=[], id="throughput-sparkline")

                yield Label("Provisioning: Idle", id="provision-status")

            yield Static("Press [b]F5[/b] to Start/Stop Server & Auto-Provision", id="status-hint")

    def on_select_changed(self, event: "Select.Changed") -> None:
        """Handle selection changes."""
        if event.select.id == "select-protocol":
            self.protocol = str(event.value)
            # Update default port based on protocol
            port_input = self.query_one("#input-port", Input)
            if self.protocol == "TCP":
                port_input.value = "9000"
            elif self.protocol == "HTTP":
                port_input.value = "9001"
            elif self.protocol == "UDP":
                port_input.value = "9002"
        elif event.select.id == "select-agent-type":
            self.agent_type = str(event.value)
            # Re-trigger layout watcher
            self.watch_agent_type(self.agent_type)

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        if self.device_id:
            try:
                self.query_one("#input-host", Input).value = self.device_id
            except Exception:
                pass
        self.protocol = self.initial_protocol
        self.agent_type = self.initial_agent_type

        # Explicitly trigger layout sync
        self.watch_agent_type(str(self.agent_type))

    def watch_agent_type(self, agent_type: Any) -> None:
        if self._is_unmounting:
            return

        agent_type = str(agent_type)
        try:
            # Hide all dynamic rows first
            for row_id in ["#row-live", "#row-logics", "#row-status"]:
                try:
                    self.query_one(row_id, Horizontal).display = False
                except Exception:
                    pass

            # Reveal the correct row
            if agent_type == "LIVE_DATA":
                self.query_one("#row-live", Horizontal).display = True
                self.query_one("#card-frames", StatCard).update_label("TOTAL FRAMES")
            elif agent_type == "LOGICS":
                self.query_one("#row-logics", Horizontal).display = True
                self.query_one("#card-frames", StatCard).update_label("TOTAL PACKETS")
            elif agent_type == "STATUS":
                self.query_one("#row-status", Horizontal).display = True
                self.query_one("#card-frames", StatCard).update_label("TOTAL PACKETS")
            elif agent_type == "RECORDING":
                # Recording uses same row as status or its own?
                # Let's use the status row for basic info but update labels
                self.query_one("#row-status", Horizontal).display = True
                self.query_one("#card-frames", StatCard).update_label("TOTAL PAYLOADS")
                # Reset these to N/A for recording if not already set
                self.sensor_temp = "N/A"
                self.sensor_uptime = "0.0"
                self.dropped_pkts = 0

            # Reset metrics
            self.frame_count = 0
            self.seq_id = 0
            self.total_bytes = 0
            self.total_events = 0
            self.current_tracks_person = 0
            self.current_tracks_group = 0
            self.active_logics = 0
            self.logics_fw = 0
            self.logics_bw = 0
            self.logics_visits = 0
            self.logics_dwell = 0.0
            self.push_interval = 0.0
            self.sensor_temp = "N/A"
            self.sensor_uptime = "0.0"
            self.dropped_pkts = 0
            self.events_breakdown = {}
            self.logic_samples = (0, 0)
            self.sensor_fw = "N/A"
            self.throughput = 0.0
            self.throughput_avg = 0.0
            self.throughput_max = 0.0
            self.throughput_min = -1.0

        except Exception:
            pass

    def watch_current_tracks_person(self, count: int) -> None:
        try:
            self.query_one("#card-persons", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_current_tracks_group(self, count: int) -> None:
        try:
            self.query_one("#card-groups", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_active_logics(self, count: int) -> None:
        try:
            self.query_one("#card-active-logics", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_logics_fw(self, count: int) -> None:
        try:
            self.query_one("#card-fw", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_logics_bw(self, count: int) -> None:
        try:
            self.query_one("#card-bw", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_logics_visits(self, count: int) -> None:
        try:
            self.query_one("#card-visits", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_logics_dwell(self, dwell: float) -> None:
        try:
            self.query_one("#card-dwell", StatCard).update_value(f"{dwell:.1f}")
        except Exception:
            pass

    def watch_push_interval(self, interval: float) -> None:
        try:
            self.query_one("#card-interval", StatCard).update_value(f"{interval:.1f}")
        except Exception:
            pass

    def watch_sensor_temp(self, temp: str) -> None:
        try:
            self.query_one("#card-temp", StatCard).update_value(str(temp))
        except Exception:
            pass

    def watch_events_breakdown(self, breakdown: dict) -> None:
        try:
            parts = [f"{k}: {v}" for k, v in breakdown.items()]
            val = " | ".join(parts) if parts else "None"
            # Prevent overflow layout breaking
            if len(val) > 25:
                val = val[:22] + "..."
            self.query_one("#card-events", StatCard).update_value(val)
        except Exception:
            pass

    def watch_seq_id(self, seq: int) -> None:
        try:
            self.query_one("#card-seq", StatCard).update_value(str(seq))
        except Exception:
            pass

    def watch_logic_samples(self, samples: tuple) -> None:
        try:
            self.query_one("#card-samples", StatCard).update_value(f"{samples[0]}/{samples[1]}")
        except Exception:
            pass

    def watch_sensor_fw(self, fw: str) -> None:
        try:
            self.query_one("#card-firmware", StatCard).update_value(fw)
        except Exception:
            pass

    def watch_sensor_uptime(self, uptime: str) -> None:
        try:
            self.query_one("#card-uptime", StatCard).update_value(uptime)
        except Exception:
            pass

    def watch_dropped_pkts(self, count: int) -> None:
        try:
            self.query_one("#card-dropped", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_frame_count(self, count: int) -> None:
        if self._is_unmounting:
            return
        try:
            self.query_one("#card-frames", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_total_events(self, count: int) -> None:
        try:
            self.query_one("#card-events", StatCard).update_value(str(count))
        except Exception:
            pass

    def watch_throughput(self, throughput: float) -> None:
        if self._is_unmounting:
            return
        try:
            val = (
                f"{throughput} B/s"
                if throughput < 1024
                else f"{throughput / 1024:.1f} KB/s"
                if throughput < 1024 * 1024
                else f"{throughput / (1024 * 1024):.1f} MB/s"
            )
            self.query_one("#card-throughput", StatCard).update_value(val)

            spark = self.query_one("#throughput-sparkline", Sparkline)
            self._throughput_history.append(throughput)
            if len(self._throughput_history) > 50:
                self._throughput_history.pop(0)
            spark.data = self._throughput_history
        except Exception:
            pass

    def watch_throughput_avg(self, avg: float) -> None:
        try:
            min_val = self.throughput_min if self.throughput_min >= 0 else 0.0
            max_val = self.throughput_max

            def fmt(v):
                return f"{v / 1024:.1f}" if v >= 1024 else f"{v:.0f}"

            unit = "KB/s" if max_val >= 1024 else "B/s"

            val_str = f"{fmt(avg)} | {fmt(min_val)} | {fmt(max_val)}"
            self.query_one("#card-analytics", StatCard).update_value(f"{val_str} [dim]{unit}[/dim]")
        except Exception:
            pass

    def watch_fps(self, fps: float) -> None:
        if self._is_unmounting:
            return
        try:
            self.query_one("#card-fps", StatCard).update_value(f"{fps:.1f}")
        except Exception:
            pass

    def watch_provisioning_status(self, status: str) -> None:
        """Reactive watcher for provisioning status."""
        if self._is_unmounting:
            return
        try:
            label = self.query_one("#provision-status", Label)
            label.update(f"Provisioning: {status}")
            if "Success" in status:
                label.styles.color = "green"
            elif "Failed" in status:
                label.styles.color = "red"
            elif "Active" in status:
                label.styles.color = "yellow"
            else:
                label.styles.color = "gray"
        except Exception:
            pass

    def watch_is_active(self, active: bool) -> None:
        """Reactive watcher for server state."""
        if self._is_unmounting:
            return
        try:
            hint = self.query_one("#status-hint", Static)
            if active:
                hint.update("Server [b][GREEN]ACTIVE[/][/] - Listening for sensors...")
                self.add_class("server-active")
            else:
                hint.update("Server [b][RED]INACTIVE[/][/] - Press F5 to start")
                self.remove_class("server-active")
        except Exception:
            # DOM nodes might be gone during unmount
            pass

    async def action_toggle_server(self) -> None:
        """Starts or stops the XovisTCPServer."""
        if self.is_active:
            await self.stop_server()
        else:
            await self.start_server()

    async def start_server(self) -> None:
        """Instantiates and starts the server, then provisions the sensor."""
        from textual.widgets import Select

        self.protocol = self.query_one("#select-protocol", Select).value
        agent_type = self.query_one("#select-agent-type", Select).value
        context_type = self.query_one("#select-context", Select).value
        host = self.query_one("#input-host", Input).value
        port_str = self.query_one("#input-port", Input).value
        user = "admin"
        password = self.query_one("#input-pass", Input).value
        agent_name = self.query_one("#input-name", Input).value

        from textual.widgets import Checkbox

        debug_mode = self.query_one("#check-debug", Checkbox).value

        try:
            port = int(port_str)
        except ValueError:
            self.app.notify("Invalid port number", severity="error")
            return

        if self.protocol == "TCP":
            from xovis.datapush.tcp_server import XovisTCPServer

            self.server = XovisTCPServer()
        elif self.protocol == "UDP":
            from xovis.datapush.udp_server import XovisUDPServer

            self.server = XovisUDPServer()
        elif self.protocol == "HTTP":
            from xovis.datapush.http_server import XovisHTTPServer

            self.server = XovisHTTPServer()

        self.server.attach_sink(MetricSink(self, agent_type=str(agent_type), debug=debug_mode))

        self.is_active = True

        # Start server with bind check
        try:
            # We use a Future to wait for the server to actually start or fail
            start_fut = asyncio.get_running_loop().create_future()

            async def run_server():
                try:
                    # The server start method is awaited inside this task
                    # but we need to catch the bind error early.
                    # For TCP/HTTP, the initial bind happens within the start() call.
                    # We wrap the server start in another task to allow catching the error.
                    await self.server.start(port=port)
                except Exception as e:
                    if not start_fut.done():
                        start_fut.set_exception(e)
                    raise

            self._server_task = asyncio.create_task(run_server())

            # Give it a tiny moment to bind
            try:
                # We wait briefly to see if it crashes immediately (e.g. port busy)
                if self._server_task:
                    await asyncio.wait_for(asyncio.shield(self._server_task), timeout=0.2)
            except asyncio.TimeoutError:
                # If it didn't crash in 200ms, it's likely bound successfully
                if not start_fut.done():
                    start_fut.set_result(True)
            except Exception as e:
                # Caught an immediate startup error (like OSError: [Errno 10048])
                self.is_active = False
                self.server = None
                self._server_task = None
                error_msg = str(e)
                if "10048" in error_msg or "address already in use" in error_msg.lower():
                    self.app.notify(
                        f"Port {port} is already in use. Please choose another port.",
                        severity="error",
                    )
                else:
                    self.app.notify(f"Failed to start server: {escape(str(e))}", severity="error")
                if not start_fut.done():
                    start_fut.set_result(False)  # type: ignore
                return

        except Exception as e:
            self.is_active = False
            self.app.notify(f"Critical server startup failure: {escape(str(e))}", severity="error")
            return

        if hasattr(self.app, "background_tasks"):
            self.app.background_tasks.add(self._server_task)
            self._server_task.add_done_callback(self.app.background_tasks.discard)

        self._metrics_task = asyncio.create_task(self._calculate_metrics())

        self.app.notify(f"Xovis {self.protocol} Server started on port {port}")

        # Auto-provision sensor (Always ON if host is provided)
        if host:
            provision_task = asyncio.create_task(
                self._provision_sensor(
                    host,
                    user,
                    password,
                    port,
                    agent_name,
                    self.protocol,
                    str(agent_type),
                    str(context_type),
                    debug_mode,
                )
            )
            if hasattr(self.app, "background_tasks"):
                self.app.background_tasks.add(provision_task)
                provision_task.add_done_callback(self.app.background_tasks.discard)
        else:
            self.provisioning_status = "Skipped (No Host IP)"

    async def _provision_sensor(
        self,
        host: str,
        user: str,
        password: str,
        port: int,
        agent_name: str,
        protocol: str = "TCP",
        agent_type: str = "LIVE_DATA",
        context_type: str = "Singlesensor",
        debug_mode: bool = False,
    ) -> None:
        """Configures the Xovis sensor to datapush data to this TUI instance.

        Args:
            host (str): Sensor IP.
            user (str): Sensor username.
            password (str): Sensor password.
            port (int): Target port.
            agent_name (str): The name of the DataPush agent.
            protocol (str): Transport protocol.
            agent_type (str): The type of agent (LIVE_DATA, LOGICS, STATUS).
            context_type (str): The target context (Singlesensor, Multisensor).
            debug_mode (bool): Whether to enable debug logging.
        """
        import socket

        import httpx
        from textual.widgets import Select

        from xovis.api.core.exceptions import HardwareNotSupportedError
        from xovis.models.device import (
            AgentConfig,
            DataConfig,
            DataFormat,
            DataFormatType,
            HTTPConfig,
            Scheduler,
            SchedulerType,
            TCPConfig,
            TCPUDPMode,
            UDPConfig,
        )

        # Resolve Callback IP
        try:
            selected_ip = str(self.query_one("#select-callback", Select).value)
        except Exception:
            selected_ip = "AUTO"

        if selected_ip == "AUTO":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()
        else:
            local_ip = selected_ip

        conn_name = f"SDK-TUI-{port}"
        self.provisioning_status = "Active (Connecting...)"

        if debug_mode:
            try:
                with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"--- Provisioning started: host={host}, local_ip={local_ip}, port={port}, protocol={protocol} ---\n")
            except Exception:
                pass

        try:
            async with DeviceClient(host, user, password) as client:
                # Resolve target context
                target_ctx = None
                if context_type == "Multisensor":
                    ms_contexts = await client.multisensors.sync()
                    if not ms_contexts:
                        # Fallback to cache if sync returned nothing but we have something cached
                        if hasattr(client.multisensors, "_contexts") and client.multisensors._contexts:
                            target_ctx = list(client.multisensors._contexts)[0]
                        else:
                            raise ValueError("No multisensor environment found on this device.")
                    else:
                        target_ctx = ms_contexts[0]

                    self.app.notify(f"Targeting Multisensor: {escape(target_ctx.name)}")
                else:
                    # Explicitly check for Spider before using singlesensor
                    if client.is_spider:
                        # Spiders MUST use multisensor. If user forced Singlesensor, it's an error.
                        raise HardwareNotSupportedError("Spider NUCs lack physical lenses. Please select 'Multisensor' context.")
                    target_ctx = client.singlesensor

                # Force cleanup of existing TUI agents/connections
                try:
                    await target_ctx.datapush.delete_agent(agent_name)
                except Exception:
                    pass
                try:
                    await target_ctx.datapush.delete_connection(conn_name)
                except Exception:
                    pass

                # 1. Connection
                if protocol == "TCP":
                    conn = DataPushConnection(
                        name=conn_name,
                        protocol="TCP",
                        config=TCPConfig(mode=TCPUDPMode.CLIENT, uri=f"tcp://{local_ip}", port=port),
                    )
                elif protocol == "UDP":
                    # Prefix with udp:// as per Agent Instructions
                    conn = DataPushConnection(
                        name=conn_name,
                        protocol="UDP",
                        config=UDPConfig(mode=TCPUDPMode.CLIENT, uri=f"udp://{local_ip}", port=port),
                    )
                elif protocol == "HTTP":
                    # Rule: HTTP uri MUST NOT contain port, port must be in port field.
                    # Current code: HTTPConfig(uri=f"http://{local_ip}/webhook", port=port) - this is correct.
                    conn = DataPushConnection(
                        name=conn_name,
                        protocol="HTTP",
                        config=HTTPConfig(uri=f"http://{local_ip}/webhook", port=port),
                    )
                else:
                    raise ValueError(f"Unsupported protocol: {protocol}")

                await target_ctx.datapush.create_connection(conn, id_mode="SERVER")

                # Resolve ID for the newly created connection
                conn_id = await target_ctx.datapush._resolve_connection_id(conn_name)
                # Ensure it's an integer for DataPushAgent validation
                conn_id = int(conn_id) if conn_id is not None else None

                # 2. Agent
                from xovis.models.device import DataPushType, IntervalType, RetryConfig, RetryMode

                if agent_type == "LIVE_DATA":
                    scheduler = Scheduler(type=SchedulerType.IMMEDIATE)
                    data = DataConfig(
                        format=DataFormat(type=DataFormatType.JSON),
                        resolution="MAX",
                        empty_frames="PUSH_ALL_FRAMES",
                    )
                elif agent_type == "LOGICS":
                    scheduler = Scheduler(type=SchedulerType.INTERVAL, interval=IntervalType.ONE_MINUTE)
                    data = DataConfig(format=DataFormat(type=DataFormatType.JSON), resolution="ONE_MINUTE")
                elif agent_type == "STATUS":
                    scheduler = Scheduler(type=SchedulerType.INTERVAL, interval=IntervalType.FIVE_SECONDS)
                    data = DataConfig(format=DataFormat(type=DataFormatType.JSON), resolution="MAX")
                elif agent_type == "RECORDING":
                    # User provided config for RECORDING
                    scheduler = Scheduler(
                        type=SchedulerType.INTERVAL,
                        interval=IntervalType.ONE_MINUTE,
                        retry=RetryConfig(
                            mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                            max_number=12,
                            reset_on_next_push_schedule=True,
                            delay_start_min=2.0,
                            delay_start_max=2.0,
                            delay_increase_factor=2.0,
                        ),
                    )
                    data = DataConfig(
                        format=DataFormat(type=DataFormatType.RECORDING, version="5.0", time="UNIX_TIME_MS"),
                        resolution="MAX",
                        package_size=1,
                    )
                else:
                    raise ValueError(f"Unknown agent type: {agent_type}")

                agent = DataPushAgent(
                    name=agent_name,
                    type=DataPushType(str(agent_type)),
                    enabled=True,
                    connection=conn_id,
                    config=AgentConfig(scheduler=scheduler, data=data),
                )

                await target_ctx.datapush.create_agent(agent, id_mode="SERVER")

                self.provisioning_status = "Success (Agent Configured)"
                self.app.notify(f"Sensor {host} provisioned successfully")

        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            reason = e.response.reason_phrase
            clean_msg = f"HTTP {code} {reason}"

            if code in (401, 403):
                self.provisioning_status = "Failed (Auth)"
                self.app.notify(
                    f"Authentication failed: {escape(clean_msg)}. Check sensor password.",
                    severity="error",
                )
            else:
                self.provisioning_status = f"Failed ({code})"
                self.app.notify(f"Provisioning rejected: {escape(clean_msg)}", severity="warning")

            if debug_mode:
                try:
                    with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"--- Provisioning failed (HTTP): {clean_msg} ---\n")
                except Exception:
                    pass

            # Auto-rollback: stop server if provisioning fails
            await self.stop_server()
        except Exception as e:
            # Replaced XovisAuthError with a string check to prevent unimported exceptions from breaking the loop
            err_type = type(e).__name__
            if "Auth" in err_type:
                self.provisioning_status = "Failed (Auth)"
                self.app.notify("Authentication failed. Check sensor password.", severity="error")
            else:
                self.provisioning_status = f"Failed ({err_type})"
                # Log the EXACT error to the UI so we can debug SDK schema changes
                self.app.notify(f"Network/Schema Error: {err_type} - {escape(str(e))}", severity="warning")

            if debug_mode:
                try:
                    with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"--- Provisioning failed ({err_type}): {str(e)} ---\n")
                except Exception:
                    pass

            await self.stop_server()

    async def stop_server(
        self,
        host: str = "",
        user: str = "admin",
        password: str = "",
        port_str: str = "",
        agent_name: str = "",
        context_type: str = "",
    ) -> None:
        """Gracefully shuts down the TCP server and cleans up sensor config."""
        if not self.is_active and not self._server_task:
            return

        # Try to get values from state if not provided as arguments
        # This is more reliable during unmount
        try:
            # We check if they are provided, if not we try to use what we had during start_server
            # or what is currently in the inputs.
            host = host or str(self.query_one("#input-host", Input).value)
            user = user or "admin"
            password = password or str(self.query_one("#input-pass", Input).value)
            port_str = port_str or str(self.query_one("#input-port", Input).value)
            agent_name = agent_name or str(self.query_one("#input-name", Input).value)
            from textual.widgets import Select

            context_type = context_type or str(self.query_one("#select-context", Select).value)
        except Exception:
            # Fallback to whatever was passed in
            pass

        # 1. Remote Cleanup (Non-blocking)
        if host:
            from textual.widgets import Checkbox

            try:
                keep_alive = self.query_one("#check-keep", Checkbox).value
            except Exception:
                keep_alive = False

            if not keep_alive:
                try:
                    port = int(str(port_str))
                    self.provisioning_status = "Cleaning up..."
                    # Check for "pass" default and try to get actual password if it was empty
                    # but typically if it is "pass", it's what's in the input field.
                    # The issue might be that stop_server is called during unmount with empty password
                    # if the query fails.
                    cleanup_task = asyncio.create_task(self._cleanup_sensor(host, user, password, port, agent_name, str(context_type)))
                    if hasattr(self.app, "background_tasks"):
                        self.app.background_tasks.add(cleanup_task)
                        cleanup_task.add_done_callback(self.app.background_tasks.discard)
                except (ValueError, TypeError):
                    pass
            else:
                self.provisioning_status = "Left Active (Keep on Exit)"

        # 2. Local Server Shutdown (CRITICAL)
        if self.server and hasattr(self.server, "stop"):
            try:
                # Force the server to unbind the port BEFORE cancelling the task
                if asyncio.iscoroutinefunction(self.server.stop):
                    await asyncio.wait_for(self.server.stop(), timeout=1.5)
                else:
                    self.server.stop()
            except Exception:
                pass

        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                # Wait for the task to fully abort and release the socket
                await asyncio.wait_for(self._server_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
            self._server_task = None

        if self._metrics_task:
            self._metrics_task.cancel()
            self._metrics_task = None

        self.is_active = False
        self.app.notify("Telemetry Server stopped")

    async def _cleanup_sensor(
        self,
        host: str,
        user: str,
        password: str,
        port: int,
        agent_name: str,
        context_type: str = "Singlesensor",
    ) -> None:
        """Removes the DataPush agent and connection from the sensor.

        Args:
            host (str): Sensor IP.
            user (str): Sensor username.
            password (str): Sensor password.
            port (int): The port used for this session.
            agent_name (str): The name of the DataPush agent.
            context_type (str): The target context (Singlesensor, Multisensor).
        """
        import httpx

        conn_name = f"SDK-TUI-{port}"
        try:
            async with DeviceClient(host, user, password) as client:
                # Resolve target context
                target_ctx = client.singlesensor
                if context_type == "Multisensor":
                    ms_contexts = await client.multisensors.sync()
                    if ms_contexts:
                        target_ctx = ms_contexts[0]
                    elif hasattr(client.multisensors, "_contexts") and client.multisensors._contexts:
                        target_ctx = list(client.multisensors._contexts)[0]
                    else:
                        # If no MS found during cleanup, we can't do much
                        return

                # 1. Delete Agent
                agent_collection = await target_ctx.datapush.get_all_agents()
                agents = agent_collection.agents or []
                for a in agents:
                    if a.name == agent_name:
                        await target_ctx.datapush.delete_agent(a.id)
                        break

                # 2. Delete Connection
                connection_collection = await target_ctx.datapush.get_all_connections()
                connections = connection_collection.connections or []
                for c in connections:
                    if c.name == conn_name:
                        await target_ctx.datapush.delete_connection(c.id)
                        break

                self.provisioning_status = "Idle (Cleaned up)"
                self.app.notify(f"Sensor {host} cleaned up")
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            self.provisioning_status = f"Cleanup Failed (HTTP {code})"
            self.app.notify(f"Sensor cleanup failed: HTTP {code}", severity="warning")
        except Exception as e:
            # Replaced XovisAuthError with a string check to prevent unimported exceptions from breaking the loop
            err_type = type(e).__name__
            if "Auth" in err_type:
                self.provisioning_status = "Cleanup Failed (Auth)"
                self.app.notify("Sensor cleanup failed: Authentication Error", severity="error")
            else:
                self.provisioning_status = f"Cleanup Failed ({err_type})"
                self.app.notify(f"Sensor cleanup failed: {err_type} - {escape(str(e))}", severity="warning")

    async def _calculate_metrics(self) -> None:
        """Background task to calculate FPS and throughput based on frame ingestion."""
        last_count = self.frame_count
        last_bytes = self.total_bytes
        total_throughput_samples = 0
        sum_throughput = 0.0

        while True:
            await asyncio.sleep(1.0)
            current_count = self.frame_count
            current_bytes = self.total_bytes

            if current_count == last_count:
                self.fps = 0.0
                self.throughput = 0.0
            else:
                self.fps = float(current_count - last_count)
                self.throughput = float(current_bytes - last_bytes)

                # Update advanced analytics only when data is flowing
                total_throughput_samples += 1
                sum_throughput += self.throughput
                self.throughput_avg = sum_throughput / total_throughput_samples

                if self.throughput > self.throughput_max:
                    self.throughput_max = self.throughput
                if self.throughput_min < 0 or self.throughput < self.throughput_min:
                    self.throughput_min = self.throughput

            last_count = current_count
            last_bytes = current_bytes

    async def on_unmount(self) -> None:
        """Ensures server shutdown on widget destruction."""
        self._is_unmounting = True
        # Pre-extract values because they might be gone when stop_server runs
        host = ""
        user = "admin"
        password = ""
        port_str = ""
        agent_name = ""
        context_type = ""

        try:
            # We use query() and check length to avoid NoMatches exception
            host_input = self.query("#input-host")
            if host_input and hasattr(host_input.first(), "value"):
                host = str(host_input.first().value)  # type: ignore

            pass_input = self.query("#input-pass")
            if pass_input and hasattr(pass_input.first(), "value"):
                password = str(pass_input.first().value)  # type: ignore

            port_input = self.query("#input-port")
            if port_input and hasattr(port_input.first(), "value"):
                port_str = str(port_input.first().value)  # type: ignore

            name_input = self.query("#input-name")
            if name_input and hasattr(name_input.first(), "value"):
                agent_name = str(name_input.first().value)  # type: ignore

            ctx_select = self.query("#select-context")
            if ctx_select and hasattr(ctx_select.first(), "value"):
                context_type = str(ctx_select.first().value)  # type: ignore

            await self.stop_server(host, user, password, port_str, agent_name, context_type)
        except Exception:
            # Fallback to stop_server without parameters
            await self.stop_server()
