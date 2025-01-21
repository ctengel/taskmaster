"""A TUI for KanBan using Textual"""

from typing import Any
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button
from textual.containers import HorizontalScroll, VerticalScroll
import requests

class KanList(VerticalScroll):
    """A vertically scrolling kanban column of cards"""

    def __init__(self, *args: Any, list_url: str, **kwargs: Any):
        self.kba_url = list_url
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        cards = requests.get(self.kba_url, timeout=1).json()['cards']
        for card in cards:
            yield Button(card['card_name'])


class KanBanApp(App):
    """A Textual app to manage KanBan boards"""

    CSS_PATH = "kantui.tcss"

    #BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield HorizontalScroll(KanList(list_url="http://127.0.0.1:8000/lists/1"),
                               KanList(list_url="http://127.0.0.1:8000/lists/2"))

    #def action_toggle_dark(self) -> None:
    #    """An action to toggle dark mode."""
    #    self.theme = (
    #        "textual-dark" if self.theme == "textual-light" else "textual-light"
    #    )


if __name__ == "__main__":
    app = KanBanApp()
    app.run()
