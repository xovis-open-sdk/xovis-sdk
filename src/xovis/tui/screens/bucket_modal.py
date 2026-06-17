"""
Xovis SDK - State Bucket Management Modal

This module provides a ModalScreen for managing fleet State Buckets. It allows
users to save, load, and delete offline JSON buckets representing filtered
fleet views and their discovered Layer 2.5 topologies.
"""

import os

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView


class BucketModal(ModalScreen[tuple[str, str]]):
    """Modal screen for managing Hub and Host State Buckets.

    Scans the current working directory for *.state.json files, maintaining
    strict alignment with the State & Topology Plane's persistence patterns.
    """

    CSS = """
    BucketModal {
        align: center middle;
    }
    #modal-container {
        width: 80;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #modal-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
    }
    #bucket-list {
        height: 10;
        border: solid $primary;
        margin-bottom: 1;
    }
    .modal-buttons {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    .modal-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Back", priority=True),
    ]

    def __init__(self, suggested_name: str, device_count: int = 0) -> None:
        """Initializes the BucketModal.

        Args:
            suggested_name (str): The default name to populate the input field with.
            device_count (int): The number of devices currently filtered, to enforce limits.
        """
        super().__init__()
        self.suggested_name = suggested_name
        self.device_count = device_count
        from pathlib import Path

        res_dir = Path("_local_resources") / "states"
        try:
            res_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if res_dir.exists() and os.access(res_dir, os.W_OK):
            self.target_dir = str(res_dir.resolve())
        else:
            self.target_dir = os.getcwd()

    def compose(self) -> ComposeResult:
        """Hydrates the modal layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        with Vertical(id="modal-container"):
            yield Label("State Bucket Management", id="modal-title")
            yield ListView(id="bucket-list")
            yield Input(
                id="bucket-name",
                value=self.suggested_name,
                placeholder="Bucket name (without .state.json)...",
            )

            save_btn = Button("Save View to Bucket", id="btn-save", variant="primary")
            if self.device_count > 350:
                save_btn.disabled = True
                save_btn.tooltip = "Cannot save bucket with more than 350 devices."

            yield Horizontal(
                save_btn,
                Button("Load Bucket", id="btn-load", variant="success"),
                Button("Delete Bucket", id="btn-delete", variant="error"),
                Button("Back", id="btn-back", variant="default"),
                classes="modal-buttons",
            )

    def on_mount(self) -> None:
        """Populates the list from the local directory."""
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Reads the directory for *.state.json files and updates the ListView."""
        list_view = self.query_one("#bucket-list", ListView)
        list_view.clear()

        files = sorted([f[:-11] for f in os.listdir(self.target_dir) if f.endswith(".state.json")])
        for file_name in files:
            item = ListItem(Label(file_name))
            item.bucket_name = file_name
            list_view.append(item)

    @on(ListView.Selected)
    def on_list_selected(self, event: ListView.Selected) -> None:
        """Updates the input field when a bucket is selected."""
        if event.item:
            name = getattr(event.item, "bucket_name", "")
            if name:
                self.query_one("#bucket-name", Input).value = name

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles action buttons and dismisses the modal."""
        action = event.button.id.replace("btn-", "") if event.button.id else ""
        if action == "back":
            self.dismiss(None)
            return

        name = self.query_one("#bucket-name", Input).value.strip()
        if name:
            self.dismiss((action, name))
        else:
            self.query_one("#bucket-name", Input).focus()
