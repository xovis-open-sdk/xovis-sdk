"""
Xovis SDK - Local Network Scanner Modal

This module provides a modal screen for configuring and launching a local network
discovery scan.
"""

import ipaddress
import socket
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select


class ScannerModal(ModalScreen[Optional[tuple[str, int]]]):
    """A modal screen for local network discovery settings.

    Allows the user to select from available local networks or specify a starting
    IP address and a host count for scanning the local network for Xovis devices.
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Back", priority=True),
    ]

    def _get_local_networks(self) -> list[tuple[str, str]]:
        """Discovers local IPv4 networks available on the host.

        Returns:
            List[Tuple[str, str]]: A list of (display_name, network_start_ip) pairs.
        """
        networks = []
        try:
            _, _, ips = socket.gethostbyname_ex(socket.gethostname())
            for ip in ips:
                try:
                    # Assume /24 for simplicity if we can't get the mask
                    net = ipaddress.IPv4Interface(f"{ip}/24").network
                    networks.append((f"{ip} (Network: {net})", str(net.network_address + 1)))
                except ValueError:
                    continue
        except Exception:
            pass

        if not networks:
            networks.append(("No networks found", "10.0.0.1"))
        return networks

    def compose(self) -> ComposeResult:
        """Hydrates the modal layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        networks = self._get_local_networks()
        default_ip = networks[0][1] if networks else "10.0.0.1"

        with Vertical(id="scanner-container"):
            yield Label("Local Network Discovery")
            yield Label("Select Network:", classes="field-label")
            yield Select(
                options=[(name, ip) for name, ip in networks],
                prompt="Choose a network...",
                id="network-select",
            )
            yield Label("Or Enter Manually:", classes="field-label")
            yield Input(id="scan-ip", value=default_ip, placeholder="Start IP")
            yield Input(id="scan-count", value="255", placeholder="Host Count")
            with Horizontal(id="scanner-buttons"):
                yield Button("Scan", id="btn-scan", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="error")

    @on(Select.Changed)
    def on_network_selected(self, event: Select.Changed) -> None:
        """Updates the manual input fields when a network is selected.

        Args:
            event (Select.Changed): The selection change event.
        """
        if event.value:
            self.query_one("#scan-ip", Input).value = str(event.value)
            self.query_one("#scan-count", Input).value = "255"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button press events.

        Args:
            event (Button.Pressed): The button press event.
        """
        if event.button.id == "btn-scan":
            ip = self.query_one("#scan-ip", Input).value.strip()
            count_str = self.query_one("#scan-count", Input).value.strip()
            try:
                count = int(count_str)
                self.dismiss((ip, count))
            except ValueError:
                self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
