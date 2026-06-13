"""
Xovis SDK - Transmission Check & Throughput Optimization

This module provides tools to monitor, visualize, and optimize the throughput
of Xovis telemetry datapush. It includes a specialized sink for metric collection
and a Textual-based TUI for real-time visualization.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, Label, Static

from xovis.datapush.sinks import XovisSink
from xovis.tui.widgets.datapush_studio import DatapushStudio


@dataclass
class TransmissionStats:
    """Holds real-time transmission metrics."""

    frame_count: int = 0
    event_count: int = 0
    total_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    last_frame_time: float = 0.0
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def uptime(self) -> float:
        """
        Calculates the elapsed time since metrics collection began.

        Returns:
            float: Total seconds of active monitoring.
        """
        return time.time() - self.start_time

    @property
    def fps(self) -> float:
        """
        Calculates the average frame ingestion rate.

        Returns:
            float: Average frames per second (FPS).
        """
        return self.frame_count / self.uptime if self.uptime > 0 else 0.0

    @property
    def throughput_kbps(self) -> float:
        """
        Calculates the estimated network throughput.

        Returns:
            float: Data rate in Kilobits per second (Kbps).
        """
        return (self.total_bytes / 1024) / self.uptime if self.uptime > 0 else 0.0


class TransmissionCheckSink(XovisSink):
    """
    A specialized sink for monitoring stream performance metrics.

    Tracks frames per second, events, and estimated throughput.
    """

    def __init__(self):
        """Initializes the metrics sink and synchronization primitives."""
        self.stats = TransmissionStats()
        self._lock = asyncio.Lock()

    async def on_frame(self, frame: dict) -> None:
        """Updates frame metrics."""
        async with self._lock:
            self.stats.frame_count += 1
            now = time.time()
            if self.stats.last_frame_time > 0:
                self.stats.latencies.append(now - self.stats.last_frame_time)
            self.stats.last_frame_time = now

            # Estimate size (rough approximation since it's already parsed)
            # In a real scenario, we might want to track the raw buffer size in the server.
            import json

            self.stats.total_bytes += len(json.dumps(frame))

    async def on_events(self, events: list[dict]) -> None:
        """Updates event metrics."""
        async with self._lock:
            self.stats.event_count += len(events)


class StatCard(Static):
    """
    A reactive Textual widget for displaying individual stream performance metrics.

    Features integrated label formatting and support for dynamic value updates
    driven by the parent monitor application.
    """

    def __init__(self, label: str, value: str = "0", unit: str = "", id: Optional[str] = None):
        """
        Initializes the stat card widget.

        Args:
            label (str): The descriptive header for the metric.
            value (str): Initial string representation of the value.
            unit (str): Measurement unit (e.g., 'FPS', 'KB/s').
            id (Optional[str]): Unique Textual widget identifier.
        """
        super().__init__(id=id)
        self.label = label
        self.value_text = value
        self.unit = unit

    def compose(self) -> ComposeResult:
        """
        Hydrates the widget layout.

        Yields:
            ComposeResult: The label and value widgets.
        """
        yield Label(self.label, classes="stat-label")
        yield Label(f"{self.value_text} [dim]{self.unit}[/dim]", id=f"{self.id}-value", classes="stat-value")

    def update_value(self, value: str):
        """
        Refreshes the displayed metric value.

        Args:
            value (str): The new formatted value to display.
        """
        try:
            val_label = self.query_one(f"#{self.id}-value", Label)
            val_label.update(f"{value} [dim]{self.unit}[/dim]")
        except Exception:
            pass


class TransmissionMonitorApp(App):
    """
    Textual Application for real-time transmission monitoring.
    """

    TITLE = "Xovis Stream Transmission Monitor"
    CSS = """
    Screen {
        background: #121212;
    }
    #stats-grid {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }
    StatCard {
        background: #1e1e1e;
        border: tall #333;
        padding: 1;
        height: 100%;
        align: center middle;
    }
    .stat-label {
        width: 100%;
        text-align: center;
        color: #888;
        text-style: bold;
    }
    .stat-value {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: #00ff00;
    }
    #footer {
        background: #333;
        color: #fff;
    }
    """

    def __init__(self, sink: TransmissionCheckSink, **kwargs):
        """
        Initializes the monitor application.

        Args:
            sink (TransmissionCheckSink): The metric sink providing data.
            **kwargs: Additional keyword arguments for the Textual App.
        """
        super().__init__(**kwargs)
        self.sink = sink

    def compose(self) -> ComposeResult:
        """
        Hydrates the application layout with a grid of stat cards.

        Yields:
            ComposeResult: The Header, Stat Grid, and Footer.
        """
        yield Header()
        with Container(id="stats-grid"):
            yield StatCard("THROUGHPUT", "0.0", "KB/s", id="throughput")
            yield StatCard("FRAME RATE", "0.0", "FPS", id="fps")
            yield StatCard("TOTAL FRAMES", "0", "frames", id="total-frames")
            yield StatCard("TOTAL EVENTS", "0", "events", id="total-events")
        yield Footer()

    async def on_mount(self) -> None:
        """Configures the UI refresh interval and displays a setup hint."""
        self.set_interval(0.5, self.update_stats)
        self.notify(
            "Ensure DataPush is configured on your sensor. \nMission Control can auto-provision.",
            title="Mission Control Hint",
            severity="warning",
            timeout=10.0,
        )

    async def update_stats(self) -> None:
        """
        Periodic UI worker that pulls the latest metrics from the sink.

        Handles stale data detection by marking metrics as 'STALE' if no
        frames have arrived within the last 5 seconds.
        """
        stats = self.sink.stats

        # Check if we have received any data recently
        if stats.frame_count > 0 and (time.time() - stats.last_frame_time > 5.0):
            self.query_one("#throughput", StatCard).update_value("[red]STALE[/red]")
            self.query_one("#fps", StatCard).update_value("[red]0.0[/red]")
        else:
            self.query_one("#throughput", StatCard).update_value(f"{stats.throughput_kbps:.2f}")
            self.query_one("#fps", StatCard).update_value(f"{stats.fps:.1f}")

        self.query_one("#total-frames", StatCard).update_value(f"{stats.frame_count}")
        self.query_one("#total-events", StatCard).update_value(f"{stats.event_count}")


class DatapushStudioApp(App):
    """
    Standalone Textual Application for the Xovis Open SDK Datapush Studio.

    Provides the full suite of server monitoring and autonomous sensor
    provisioning.
    """

    TITLE = "Xovis Open SDK Datapush Studio"
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        device_id: str = "",
        port: int = 9000,
        protocol: str = "TCP",
        agent_type: str = "LIVE_DATA",
        password: str = "pass",
        **kwargs,
    ):
        """Initializes the studio application."""
        super().__init__(**kwargs)
        self.device_id = device_id
        self.port = port
        self.protocol = protocol
        self.agent_type = agent_type
        self.password = password
        self.background_tasks: set[asyncio.Task] = set()

    def compose(self) -> ComposeResult:
        """Hydrates the application layout."""
        yield Header()
        yield DatapushStudio(
            device_id=self.device_id,
            initial_port=str(self.port),
            initial_protocol=self.protocol,
            initial_agent_type=self.agent_type,
            initial_password=self.password,
        )
        yield Footer()


if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description="Xovis Stream Transmission Monitor")
    parser.add_argument("--port", type=int, default=9000, help="TCP port to listen on")
    parser.add_argument("--udp", action="store_true", help="Use UDP instead of TCP")
    args = parser.parse_args()

    from xovis.datapush.tcp_server import XovisTCPServer
    from xovis.datapush.udp_server import XovisUDPServer

    async def run_monitor():
        """
        Orchestrates the monitor lifecycle: starts the server and runs the TUI.
        """
        sink = TransmissionCheckSink()
        if args.udp:
            server = XovisUDPServer()
        else:
            server = XovisTCPServer()

        server.attach_sink(sink)

        # Run server in background
        server_task = asyncio.create_task(server.start(port=args.port))

        # Give the server a moment to bind to the port
        await asyncio.sleep(0.1)

        app = TransmissionMonitorApp(sink)
        await app.run_async()

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_monitor())
