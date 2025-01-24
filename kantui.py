#!/usr/bin/env python3
"""A TUI for KanBan using Textual"""

from typing import Any
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, Input, Pretty
from textual.containers import HorizontalScroll, VerticalScroll
from textual.screen import ModalScreen
import requests

DEFAULT_CATEGORY = 1

class CardEdit(ModalScreen[str]):
    """Ask user for text of card"""

    def compose(self) -> ComposeResult:
        yield Input()

    def on_input_submitted(self) -> None:
        """Exit screen with input value"""
        self.dismiss(self.query_one(Input).value)


class KanList(VerticalScroll):
    """A vertically scrolling kanban column of cards"""

    def __init__(self, *args: Any, list_url: str, **kwargs: Any):
        self.kba_url = list_url
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        cards = requests.get(self.kba_url, timeout=1).json()['cards']
        for card in cards:
            yield Button(card['card_name'])

    def add_card(self, card_name, category_id):
        """Add a card with a given name to this list"""
        requests.post(f"{self.kba_url}/cards/",
                      json={'card_name': card_name,
                            'category_id': category_id},
                      timeout=2)
        self.mount(Button(card_name))


class KanBanApp(App):
    """A Textual app to manage KanBan boards"""

    CSS_PATH = "kantui.tcss"

    #BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    BINDINGS = [("n", "new_card", "Add a new card here")]

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

    def action_new_card(self) -> None:
        """Add a card"""
        lists = self.query("KanList")

        #print(lists.results())
        tgt_list = lists.last()
        #tgt_list = list(lists.results())[1]

        def add_card_callback(card_text: str | None) -> None:
            """Called when card edit completes"""
            tgt_list.add_card(card_text, DEFAULT_CATEGORY)

        self.push_screen(CardEdit(), add_card_callback)


if __name__ == "__main__":
    app = KanBanApp()
    app.run()
