"""
Xovis SDK - Device Dashboard Screen

Provides a fullscreen dashboard for managing a specific Xovis device.
Includes a sidebar for navigation and a main container for active tools,
including the Datapush Studio.
"""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView

from xovis.tui.widgets.datapush_studio import DatapushStudio


class DeviceDashboardScreen(Screen):
    """Fullscreen management interface for a specific Xovis device.

    Features a split-pane layout with a navigation sidebar and a dynamic
    workspace container.
    """

    active_tool = reactive("overview")

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", priority=True),
    ]

    CSS = """
    DeviceDashboardScreen Horizontal {
        height: 1fr;
    }
    DeviceDashboardScreen Vertical#sidebar {
        width: 30;
        background: $surface;
        border-right: tall $primary;
        padding: 1;
    }
    DeviceDashboardScreen Container#workspace {
        height: 1fr;
        padding: 1;
    }
    DeviceDashboardScreen .sidebar-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }
    """

    def __init__(self, device_id: str, **kwargs) -> None:
        """Initializes the dashboard screen.

        Args:
            device_id (str): The IP or MAC address of the device.
            **kwargs: Additional keyword arguments for the Screen.
        """
        super().__init__(**kwargs)
        self.device_id = device_id

    def compose(self) -> ComposeResult:
        """Hydrates the dashboard layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label(f"DEVICE: {self.device_id}", classes="sidebar-header")
                with ListView(id="sidebar-nav"):
                    yield ListItem(Label("Overview"), id="nav-overview")
                    yield ListItem(Label("Network Settings"), id="nav-network")
                    yield ListItem(Label("Datapush Studio"), id="nav-studio")

            with Container(id="workspace"):
                # Initial view
                yield Label(f"Welcome to the Dashboard for {self.device_id}")
                yield Label("Select a tool from the sidebar to begin.")

        yield Footer()

    @on(ListView.Selected, "#sidebar-nav")
    def on_nav_select(self, event: ListView.Selected) -> None:
        """Handles sidebar navigation."""
        nav_id = event.item.id
        workspace = self.query_one("#workspace", Container)

        # Clear workspace
        for child in workspace.children:
            child.remove()

        if nav_id == "nav-overview":
            workspace.mount(Label(f"Overview for {self.device_id}"))
            workspace.mount(Label("Mock Status: Online"))
            workspace.mount(Label("Mock Firmware: 5.9.2"))
        elif nav_id == "nav-network":
            workspace.mount(Label("Network Configuration"))
            workspace.mount(Label(f"IP Address: {self.device_id}"))
        elif nav_id == "nav-studio":
            workspace.mount(DatapushStudio(device_id=self.device_id))

    def action_back(self) -> None:
        """Returns to the previous screen."""
        self.app.pop_screen()
