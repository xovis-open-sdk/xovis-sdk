import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header

from xovis.api.hub.client import HubClient
from xovis.tui.screens.ai_privacy import AIPrivacyScreen
from xovis.tui.screens.fleet_explorer import XovisFleetTable


class DashboardScreen(Screen):
    """Primary landing screen for the Xovis Open SDK Mission Control.

    Offers a unified navigation path to explore the Xovis HUB Cloud fleet.
    """

    BINDINGS = [
        Binding("escape", "app.quit", "Quit", priority=True),
    ]

    def __init__(self, hub_client: Optional["HubClient"] = None, **kwargs) -> None:
        """Initializes the dashboard screen.

        Args:
            hub_client (Optional[HubClient]): The authenticated Xovis Hub client.
                Defaults to None.
            **kwargs: Additional keyword arguments for the Screen.
        """
        super().__init__(**kwargs)
        self.hub_client = hub_client

    def compose(self) -> ComposeResult:
        """Hydrates the dashboard layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        yield Header()
        with Center():
            with Middle():
                with Vertical(id="menu"):
                    yield Button("Launch Fleet Explorer", id="btn-fleet", variant="primary")
                    yield Button("AI & Privacy Settings", id="btn-privacy", variant="warning")  # Add this
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles menu navigation button presses.

        Args:
            event (Button.Pressed): The button press event payload.
        """
        if event.button.id == "btn-fleet":
            if self.hub_client:
                self.app.push_screen(XovisFleetTable(hub_client=self.hub_client))
            else:
                self.notify("Hub client not initialized. Check your credentials.", severity="error")
        elif event.button.id == "btn-privacy":
            self.app.push_screen(AIPrivacyScreen())


class XovisMissionControl(App):
    """The central entry point for the Xovis Open SDK Mission Control TUI.

    Manages screen routing, authentication state, and fleet-wide caches.
    Ensures background tasks are hard-referenced to prevent garbage collection.
    """

    TITLE = "Xovis Open SDK Mission Control"
    hub_client: Optional[HubClient] = None
    CSS = """
    Footer {
        dock: bottom;
    }
    Footer > .footer--key {
        text-style: bold;
        color: $accent;
    }
    DashboardScreen #menu {
        width: 40;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    DashboardScreen Button {
        width: 100%;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True, show=False),
    ]

    def __init__(self, **kwargs):
        """Initializes the application and background task registry.

        Args:
            **kwargs: Additional keyword arguments for the App.
        """
        super().__init__(**kwargs)
        self.background_tasks: set[asyncio.Task] = set()

    def on_mount(self) -> None:
        """Initializes the Mission Control TUI and pushes the primary dashboard."""
        load_dotenv()
        client_id = os.getenv("XOVIS_HUB_CLIENT_ID")
        client_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET")
        tunnel_url = os.getenv("XOVIS_HUB_TUNNEL_URL")

        if client_id and client_secret:
            self.notify("Hub credentials loaded successfully", severity="information")
            self.hub_client = HubClient(
                client_id=client_id,
                client_secret=client_secret,
                tunnel_base_url=tunnel_url,
            )
            # Use run_worker to avoid blocking the mount process
            self.run_worker(self.hub_client._http_client.__aenter__())
        else:
            self.notify(
                "Warning: Hub credentials (XOVIS_HUB_CLIENT_ID/CLIENT_SECRET) not found in environment",
                severity="warning",
            )

        self.install_screen(DashboardScreen(hub_client=self.hub_client), name="dashboard")
        self.push_screen("dashboard")

    def action_pop_screen(self) -> None:
        """Pops the current screen if there are more than one screens in the stack."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.notify("Already at the root screen", severity="information")

    async def on_unmount(self) -> None:
        """Ensures the HubClient is properly closed when the app exits."""
        if self.hub_client:
            await self.hub_client.aclose()
            self.hub_client = None


if __name__ == "__main__":
    app = XovisMissionControl()
    app.run()
