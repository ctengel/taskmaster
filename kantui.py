#!/usr/bin/env python3
"""A TUI for KanBan using Textual"""

import os
from typing import Any
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Button, Input
from textual.containers import HorizontalScroll, VerticalScroll
from textual.screen import ModalScreen
import requests

KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')
DEFAULT_CATEGORY = 1

class CardEdit(ModalScreen[str]):
    """Ask user for text of card"""

    default_text = None

    def __init__(self, *args: Any, default_text: str = None, **kwargs: Any):
        self.default_text = default_text
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Input(self.default_text)

    def on_input_submitted(self) -> None:
        """Exit screen with input value"""
        self.dismiss(self.query_one(Input).value)

class KanCard(Button):
    """A KanBan Card

    constructor takes card_json from API Card model
    """

    def __init__(self, *args: Any, card_json: str, **kwargs: Any):
        self.card_json = card_json
        self.card_id = card_json['card_id']
        self.manipalated = False
        super().__init__(card_json['card_name'], *args, **kwargs)

    def update_card(self, new_text):
        """Update card text both on screen and in API"""
        assert not self.manipalated
        result = requests.patch(f"{KANAPI_URL}cards/{self.card_id}",
                                json={"card_name": new_text})
        self.card_json = result.json()
        self.label = self.card_json['card_name']



class KanList(VerticalScroll):
    """A vertically scrolling kanban column of cards"""

    def __init__(self, *args: Any, list_url: str, **kwargs: Any):
        self.kba_url = list_url
        self.list_id = None
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        result = requests.get(self.kba_url, timeout=1).json()
        self.list_id = result['list_id']
        cards = result['cards']
        for card in cards:
            yield KanCard(card_json=card)

    def add_card(self, card_name, category_id):
        """Add a card with a given name to this list"""
        result = requests.post(f"{self.kba_url}/cards/",
                               json={'card_name': card_name,
                                     'category_id': category_id},
                               timeout=2)
        self.mount(KanCard(card_json=result.json()))

    def get_card_index(self, card_id: int) -> int:
        """Given a card_id, return its position in the list"""
        for index, item in enumerate(self.children):
            if item.card_id == card_id:
                return index
        assert False  # card not found
        return None


class KanBanApp(App):
    """A Textual app to manage KanBan boards"""

    CSS_PATH = "kantui.tcss"

    # TODO consider actual arrow keys instead of WASD
    BINDINGS = [("n", "new_card", "Add a new card here"),
                ("m", "move_card", "Pick up a card to move it"),
                ("a", "left_list", "<"),
                ("d", "right_list", ">"),
                ("w", "up_card", "^"),
                ("s", "down_card", "v"),
                ("c", "close_card", "Close"),
                ("e", "edit_card", "Edit")]

    selected_move_card = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        # TODO configurable board
        yield HorizontalScroll(KanList(list_url=f"{KANAPI_URL}lists/1"),
                               KanList(list_url=f"{KANAPI_URL}lists/2"))
        # TODO focus on a card

    #def action_toggle_dark(self) -> None:
    #    """An action to toggle dark mode."""
    #    self.theme = (
    #        "textual-dark" if self.theme == "textual-light" else "textual-light"
    #    )

    def current_card(self) -> KanCard:
        """Get current card or None"""
        if isinstance(self.focused, KanCard):
            return self.focused
        return None

    def current_list(self) -> KanList:
        """Get current list or None"""
        card = self.current_card()
        if card:
            return card.parent
        return None

    def action_new_card(self) -> None:
        """Add a card"""

        tgt_list = self.current_list()
        if not tgt_list:
            return

        def add_card_callback(card_text: str | None) -> None:
            """Called when card edit completes"""
            tgt_list.add_card(card_text, DEFAULT_CATEGORY)

        self.push_screen(CardEdit(), add_card_callback)

    def action_edit_card(self) -> None:
        """Edit the current card"""

        assert not self.selected_move_card

        tgt_card = self.current_card()
        if not tgt_card:
            return

        def edit_card_callback(card_text: str | None) -> None:
            """Called when card edit completes"""
            tgt_card.update_card(card_text)

        self.push_screen(CardEdit(default_text=tgt_card.card_json["card_name"]), edit_card_callback)

    def action_move_card(self) -> None:
        """Begin moving card"""
        if self.selected_move_card:
            if self.selected_move_card.manipalated:
                json_payl = {'list_id': self.selected_move_card.parent.list_id}
                idx = self.selected_move_card.parent.get_card_index(self.selected_move_card.card_id)
                if idx == 0:
                    json_payl['before_card'] = self.selected_move_card.parent.children[1].card_id
                else:
                    json_payl['after_card'] = self.selected_move_card.parent.children[idx-1].card_id
                result = requests.post(f"{KANAPI_URL}cards/{self.selected_move_card.card_id}/move",
                                       json=json_payl)
                self.selected_move_card.card_json = result.json()
                self.selected_move_card.manipalated = False
            self.selected_move_card.variant = 'default'
            self.selected_move_card = None
        else:
            tgt_card = self.current_card()
            if not tgt_card:
                return
            tgt_card.variant = "primary"
            self.selected_move_card = tgt_card

    def arrow_key(self, increase=False, list_=False):
        """Handle all keymovements

        Takes into account both simply moving the cursor as well as moving a card
        Handles both moving up and down a list and switching between lists
        """
        # TODO refactor/simplify
        curr_card = self.current_card()
        curr_list = self.current_list()
        if not (curr_card and curr_list):
            return
        tgt_list = None
        curr_pos = None
        curr_list_pos = None
        if list_:
            # Switching lists, figure out current and target list
            for index, item in enumerate(curr_list.parent.children):
                if item.kba_url == curr_list.kba_url:
                    curr_list_pos = index
            if increase and curr_list_pos == len(curr_list.parent.children) - 1:
                return
            if not increase and curr_list_pos == 0:
                return
            tgt_list = curr_list.parent.children[curr_list_pos + 1 if increase
                                                 else curr_list_pos - 1]
        else:
            # Moving within a list, just get the index
            curr_pos = curr_list.get_card_index(curr_card.card_id)
            if increase and curr_pos == len(curr_list.children) - 1:
                return
            if not increase and curr_pos == 0:
                return
        if self.selected_move_card:
            # Moving a card
            assert curr_card.card_id == self.selected_move_card.card_id
            curr_card.manipalated = True
            if list_:
                # Move to a new list by removing and recreating
                card_json = curr_card.card_json
                curr_card.remove()
                new_card = KanCard(card_json=card_json)
                new_card.manipalated = True
                tgt_list.mount(new_card)
                new_card.variant = "primary"
                new_card.focus()
                self.selected_move_card = new_card
            else:
                # Move around within current container
                if increase:
                    curr_list.move_child(curr_card, after = curr_pos + 1)
                else:
                    curr_list.move_child(curr_card, before = curr_pos - 1)
        else:
            # Just scrolling
            if list_:
                tgt_list.query(KanCard).first().focus()
            else:
                curr_list.children[curr_pos + 1 if increase else curr_pos - 1].focus()

    # These 4 functions are event handlers for each key push
    # NOTE there may be a better/cleaner way to do this

    def action_up_card(self) -> None:
        self.arrow_key()

    def action_down_card(self) -> None:
        self.arrow_key(True)

    def action_left_list(self) -> None:
        self.arrow_key(list_=True)

    def action_right_list(self) -> None:
        self.arrow_key(True, True)

    def action_close_card(self) -> None:
        """Close the current card"""
        curr_card = self.current_card()
        if not curr_card:
            return
        res = requests.post(f"{KANAPI_URL}cards/{curr_card.card_id}/close",
                            json={})
        # TODO can we avoid all-out-refresh?
        self.selected_move_card = None
        self.refresh(recompose=True)


if __name__ == "__main__":
    app = KanBanApp()
    app.run()
