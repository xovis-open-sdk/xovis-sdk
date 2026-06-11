"""
Xovis SDK - AI Privacy Configuration Screen

Provides a TUI interface for managing XovisSafetyGuardrail settings
and AIPrivacySession behaviors.
"""

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Switch,
)

from xovis.api.hub.client import HubClient
from xovis.skills.toolkit import XovisAIToolkit


class AIPrivacyScreen(Screen):
    """Configuration interface for AI Agent guardrails."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", priority=True),
        Binding("ctrl+s", "save_config", "Save Configuration", priority=True),
    ]

    CSS = """
    AIPrivacyScreen #main-container {
        padding: 1 2;
        height: 100%;
    }
    AIPrivacyScreen .section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        border-bottom: solid $primary;
        width: 100%;
    }
    AIPrivacyScreen .section-desc {
        color: $text-muted;
        margin-bottom: 1;
        text-style: italic;
    }
    AIPrivacyScreen #save-row {
        height: 3;
        margin-top: 1;
        margin-bottom: 1;
        align: right middle;
    }
    AIPrivacyScreen #btn-save {
        width: 30;
    }
    AIPrivacyScreen .setting-row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    AIPrivacyScreen .setting-label {
        width: 35;
        content-align: left middle;
    }
    AIPrivacyScreen RadioSet {
        height: auto;
        layout: horizontal;
    }
    AIPrivacyScreen RadioButton {
        margin-right: 2;
    }
    AIPrivacyScreen #tool-config-container {
        height: 25; /* Increased from 10 to allow dropdown expansion */
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    AIPrivacyScreen #tool-select-row {
        height: 3;
        margin-bottom: 1;
    }
    AIPrivacyScreen .tool-select {
        width: 60;  /* Increased width */
        margin-right: 2;
    }
    AIPrivacyScreen .safety-select {
        width: 35;
        margin-right: 2;
    }
    """

    def _get_config_path(self) -> Path:
        """Returns the path to the privacy configuration file."""
        return Path(".Redacted/ai_privacy.json")

    def _save_config(self) -> None:
        """Serializes the current UI state to disk."""
        config_data = {
            "privacy": {},
            "guardrails": {
                "dry_run": self.query_one("#switch-dryrun", Switch).value,
                "confirm": self.query_one("#switch-confirm", Switch).value,
            },
            "tool_mappings": [],
        }

        # Privacy RadioSets
        for field in ["mac", "ip", "device", "group", "customer"]:
            rs = self.query_one(f"#radio-{field}", RadioSet)
            if rs.pressed_button:
                # Extract HASH/BLOCK/ALLOW from button label or ID
                label = str(rs.pressed_button.label).upper()
                config_data["privacy"][field] = label

        # Tool Mappings Table
        table = self.query_one("#table-mappings", DataTable)
        for row_index in range(table.row_count):
            row = table.get_row_at(row_index)
            config_data["tool_mappings"].append({"tool": row[0], "safety": row[1]})

        self._get_config_path().parent.mkdir(parents=True, exist_ok=True)
        with open(self._get_config_path(), "w") as f:
            json.dump(config_data, f, indent=4)

    def _load_config(self) -> dict[str, Any]:
        """Loads the configuration from disk if it exists."""
        path = self._get_config_path()
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def compose(self) -> ComposeResult:
        # Dynamically discover all tools via reflection from the Toolkit
        # We use a HubClient dummy to ensure we see both device and fleet tools
        dummy_client = HubClient("https://api.xovis.cloud", "dummy", "dummy")
        toolkit = XovisAIToolkit(client=dummy_client)

        # Sort tools alphabetically for better UX
        sorted_tools = sorted(toolkit._tools_map.keys())
        available_tools = [(t, t) for t in sorted_tools]

        safety_levels = [
            ("OPEN", "open"),
            ("RESTRICTED", "restricted"),
            ("CRITICAL", "critical"),
            ("BLOCKED", "blocked"),
        ]

        config_data = self._load_config()
        privacy_defaults = config_data.get("privacy", {})
        guardrail_cfg = config_data.get("guardrails", {})

        yield Header()
        with ScrollableContainer(id="main-container"):
            # --- TOP SAVE ACTION ---
            with Horizontal(id="save-row"):
                yield Label("AI Safety & Privacy Policies", classes="section-header", id="top-header")
                yield Button("Save Configuration", id="btn-save", variant="primary")

            # --- PRIVACY CONFIGURATION ---
            yield Label("Data Minimization (AIPrivacySession)", classes="section-header")
            yield Label(
                "Controls how sensitive identifiers are exposed to the AI model.",
                classes="section-desc",
            )

            # Granular Fields
            for field_name in [
                "MAC Address",
                "IP Address",
                "Device Name",
                "Group / Context",
                "Customer",
            ]:
                field_key = field_name.split()[0].lower()
                saved_val = privacy_defaults.get(field_key)

                with Horizontal(classes="setting-row"):
                    yield Label(f"{field_name}:", classes="setting-label")
                    with RadioSet(id=f"radio-{field_key}"):
                        # Recommend Hash for IDs, Block for Names
                        if "MAC" in field_name or "IP" in field_name:
                            yield RadioButton(
                                "HASH",
                                value=(saved_val == "HASH" or not saved_val),
                                id=f"hash-{field_key}",
                            )
                            yield RadioButton("BLOCK", value=(saved_val == "BLOCK"), id=f"block-{field_key}")
                        else:
                            yield RadioButton("HASH", value=(saved_val == "HASH"), id=f"hash-{field_key}")
                            yield RadioButton(
                                "BLOCK",
                                value=(saved_val == "BLOCK" or not saved_val),
                                id=f"block-{field_key}",
                            )
                        yield RadioButton("ALLOW", value=(saved_val == "ALLOW"), id=f"allow-{field_key}")

            # --- GUARDRAIL CONFIGURATION ---
            yield Label("Execution Guardrails (XovisSafetyGuardrail)", classes="section-header")
            yield Label(
                "Enforces safety policies and human verification for destructive actions.",
                classes="section-desc",
            )
            with Horizontal(classes="setting-row"):
                yield Label("Enable Dry-Run Mode:", classes="setting-label")
                yield Switch(value=guardrail_cfg.get("dry_run", True), id="switch-dryrun")

            with Horizontal(classes="setting-row"):
                yield Label("Require Human Confirmation:", classes="setting-label")
                yield Switch(value=guardrail_cfg.get("confirm", True), id="switch-confirm")

            # --- TOOL SAFETY MAPPING ---
            yield Label("Tool Safety Mapping", classes="section-header")
            yield Label(
                "Assign safety levels to specific SDK methods to restrict AI capabilities.",
                classes="section-desc",
            )
            with Vertical(id="tool-config-container"):
                with Horizontal(id="tool-select-row"):
                    yield Select(
                        options=available_tools,
                        prompt="Select SDK Tool",
                        id="select-tool",
                        classes="tool-select",
                    )
                    yield Select(
                        options=safety_levels,
                        prompt="Assign Safety Level",
                        id="select-safety",
                        classes="safety-select",
                    )
                    yield Button("Save Mapping", id="btn-add-mapping", variant="success")

                # Table to show current mappings
                yield DataTable(id="table-mappings", cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table-mappings", DataTable)
        table.add_columns("SDK Tool", "Assigned Safety Level")

        config_data = self._load_config()
        mappings = {m["tool"]: m["safety"] for m in config_data.get("tool_mappings", [])}

        # Dynamically discover all tools via reflection from the Toolkit
        dummy_client = HubClient("https://api.xovis.cloud", "dummy", "dummy")
        toolkit = XovisAIToolkit(client=dummy_client)

        # Use saved safety if it exists, otherwise use auto-assigned default
        for tool_name in sorted(toolkit._tools_map.keys()):
            if tool_name in mappings:
                safety_str = mappings[tool_name]
            else:
                tool_info = toolkit._tools_map[tool_name]
                # Check for explicit 'safety_level' or extract from internal metadata if missing
                safety = tool_info.get("safety_level", "OPEN")
                safety_str = safety.name if hasattr(safety, "name") else str(safety).upper()

            table.add_row(tool_name, safety_str)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Populate the selection widgets when a row is clicked/selected."""
        row_data = event.data_table.get_row(event.row_key)
        tool_name, safety_level = row_data

        tool_select = self.query_one("#select-tool", Select)
        safety_select = self.query_one("#select-safety", Select)

        tool_select.value = tool_name
        safety_select.value = safety_level.lower()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Automatically update safety level dropdown when a tool is selected."""
        if event.select.id == "select-tool" and event.value != Select.BLANK:
            table = self.query_one("#table-mappings", DataTable)
            tool_name = str(event.value)

            # Find the safety level currently in the table for this tool
            for row_index in range(table.row_count):
                row = table.get_row_at(row_index)
                if row[0] == tool_name:
                    safety_select = self.query_one("#select-safety", Select)
                    safety_select.value = str(row[1]).lower()
                    break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_save_config()

        elif event.button.id == "btn-add-mapping":
            tool_select = self.query_one("#select-tool", Select)
            safety_select = self.query_one("#select-safety", Select)

            if tool_select.value != Select.BLANK and safety_select.value != Select.BLANK:
                table = self.query_one("#table-mappings", DataTable)
                tool_name = str(tool_select.value)
                new_safety = str(safety_select.value).upper()

                # Check if tool already exists and update it
                found = False
                for row_index in range(table.row_count):
                    row = table.get_row_at(row_index)
                    if row[0] == tool_name:
                        table.update_cell_at((row_index, 1), new_safety)
                        found = True
                        break

                if not found:
                    table.add_row(tool_name, new_safety)

                self.notify(f"Mapped {tool_name} -> {new_safety}", severity="information")
            else:
                self.notify("Please select both a Tool and a Safety Level.", severity="warning")

    def action_save_config(self) -> None:
        """Action to save configuration and exit."""
        self._save_config()
        self.notify("AI Privacy configuration saved successfully.", severity="success")
        self.app.pop_screen()
