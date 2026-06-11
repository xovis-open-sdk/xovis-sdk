"""
Xovis SDK - TUI Confirmation Modal

Provides a reusable, enterprise-grade modal dialog for critical bulk operations
within the Xovis Terminal OS. Implements the standard Textual ModalScreen pattern
with success/error variants for action confirmation.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    """A centered modal dialog for confirming critical fleet operations.

    Utilizes a grid-based layout to provide clear visual focus on the prompt
    and offers binary success/error action buttons.
    """

    CSS = """
    ConfirmModal {
        align: center middle;
    }

    #confirm-dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #confirm-prompt {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
        text-style: bold;
    }

    #button-row {
        layout: horizontal;
        height: auto;
        align: center middle;
    }

    #button-row Button {
        margin: 0 1;
        width: 16;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Back", priority=True),
    ]

    def __init__(self, prompt_text: str) -> None:
        """Initializes the modal with a custom prompt.

        Args:
            prompt_text (str): The descriptive text to display in the dialog.
        """
        super().__init__()
        self.prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        """Hydrates the modal layout.

        Yields:
            ComposeResult: The configured Textual widgets.
        """
        with Vertical(id="confirm-dialog"):
            yield Label(self.prompt_text, id="confirm-prompt")
            with Grid(id="button-row"):
                yield Button("Yes", variant="success", id="btn-yes")
                yield Button("Cancel", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles confirmation button presses.

        Args:
            event (Button.Pressed): The button press event payload.
        """
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
