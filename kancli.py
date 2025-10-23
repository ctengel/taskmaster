#!/usr/bin/env python3
"""Client for KanBan API"""

import os
import datetime
import requests
import typer

KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')

app = typer.Typer()


@app.command()
def list_(list_id: int, category_id: int = None, tabbed: bool = False, csv_: bool = False):
    """List all cards in a given list"""
    # TODO allow filter via category
    # TODO 'tabbed' output
    # TODO csv output... allow offline completion/moving?
    result = requests.get(f"{KANAPI_URL}lists/{list_id}", timeout=1)
    result.raise_for_status()
    for card in result.json()['cards']:
        print(card['card_name'])

@app.command()
def add(list_id: int, category_id: int, card: str = None):
    """Add a given card"""
    # TODO allow input multiple cards via standard input
    # TODO make usage kancli add -l LIST_ID -c CONTEXT_ID [card text]
    result = requests.post(f"{KANAPI_URL}lists/{list_id}/cards/",
                           json={'card_name': card,
                                 'category_id': category_id},
                           timeout=2)
    result.raise_for_status()
    print(result.json()['card_id'])

@app.command()
def import_(list_id: int, file_name: str, category_id: int = None, t: bool = False):
    """Import list from a file"""
    # TODO implement (match CSV output of list_()?)
    # TODO figure out what "t" is (tabbed from list_()?)
    # TODO make usage kancli import -l LIST_ID [-c CONTEXT_ID] [-t] FILE_NAME
    # TODO handle offline completion, moving, etc
    assert False

@app.command()
def new_category(category_name: str):
    """Create a new category"""
    result = requests.post(f"{KANAPI_URL}categories/",
                           json={'category_name': category_name},
                           timeout=2)
    result.raise_for_status()
    print(result.json()['category_id'])

@app.command()
def new_list(list_name: str,
             category_id: int = None,
             closed: bool = False,
             wakeup: datetime.datetime = None):
    """create a new list"""
    result = requests.post(f"{KANAPI_URL}lists/",
                           json={'list_name': list_name,
                                 'list_closed': closed,
                                 'category_id': category_id,
                                 'list_wakeup': wakeup.date().isoformat() if wakeup else None},
                           timeout=2)
    result.raise_for_status()
    print(result.json()['list_id'])

@app.command()
def lists():
    """Return all lists with their IDs"""
    result = requests.get(f"{KANAPI_URL}lists/",
                           timeout=1)
    result.raise_for_status()
    for item in result.json():
        print(item['list_id'], item['list_name'])

@app.command()
def categories():
    """Return all categories with their IDs"""
    result = requests.get(f"{KANAPI_URL}categories/",
                           timeout=1)
    result.raise_for_status()
    for item in result.json():
        print(item['category_id'], item['category_name'])

if __name__ == "__main__":
    app()
