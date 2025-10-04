#!/usr/bin/env python3
"""Client for KanBan API"""

import os
import requests
import typer

KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')

app = typer.Typer()


# TODO category/context consistency

@app.command()
def list_(list_id: int, context_id: int = None, tabbed: bool = False, csv_: bool = False):
    """List all cards in a given list"""
    # TODO allow filter via context
    # TODO 'tabbed' output
    # TODO csv output... allow offline completion/moving?
    result = requests.get(f"{KANAPI_URL}lists/{list_id}", timeout=1)
    result.raise_for_status()
    #print(result['list_name'])
    for card in result.json()['cards']:
        print(card['card_name'])

@app.command()
def add(list_id: int, context_id: int, card: str = None):
    """Add a given card"""
    # TODO allow input multiple cards via standard input
    # TODO make usage kancli add -l LIST_ID -c CONTEXT_ID [card text]
    result = requests.post(f"{KANAPI_URL}lists/{list_id}/cards/",
                           json={'card_name': card,
                                 'category_id': context_id},
                           timeout=2)
    result.raise_for_status()
    # TODO output card ID

@app.command()
def import_(list_id: int, file_name: str, context_id: int = None, t: bool = False):
    """Import list from a file"""
    # TODO implement (match CSV output of list_()?)
    # TODO figure out what "t" is (tabbed from list_()?)
    # TODO make usage kancli import -l LIST_ID [-c CONTEXT_ID] [-t] FILE_NAME
    # TODO handle offline completion, moving, etc
    assert False

@app.command()
def new_context(context_name: str):
    """Create a new context"""
    result = requests.post(f"{KANAPI_URL}categories/",
                           json={'category_name': context_name},
                           timeout=2)
    result.raise_for_status()
    print(result.json()['category_id'])

@app.command()
def new_list(list_name: str, context_id: int = None, closed: bool = False):
    """create a new list"""
    # TODO respect context and closed switches
    result = requests.post(f"{KANAPI_URL}lists/",
                           json={'list_name': list_name},
                           timeout=2)
    result.raise_for_status()
    print(result.json()['list_id'])


if __name__ == "__main__":
    app()
