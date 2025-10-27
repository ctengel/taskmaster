#!/usr/bin/env python3
"""Client for KanBan API"""

import os
import datetime
from typing import Annotated
import sys
import requests
import typer

KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')

app = typer.Typer()


@app.command("list")
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
def add(list_id: Annotated[int, typer.Option()],
        category_id:  Annotated[int, typer.Option()],
        card: Annotated[list[str], typer.Argument()] = None):
    """Add a given card"""
    if card:
        cards = [' '.join(card)]
    else:
        cards = [x.strip() for x in sys.stdin]
    for mycard in cards:
        result = requests.post(f"{KANAPI_URL}lists/{list_id}/cards/",
                               json={'card_name': mycard,
                                     'category_id': category_id},
                               timeout=2)
        result.raise_for_status()
        print(result.json()['card_id'])

@app.command("import")
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
        print(item['list_id'], item['list_name'], item['list_wakeup'])

@app.command()
def categories():
    """Return all categories with their IDs"""
    result = requests.get(f"{KANAPI_URL}categories/",
                           timeout=1)
    result.raise_for_status()
    for item in result.json():
        print(item['category_id'], item['category_name'])

@app.command()
def merge(source_list: int, dest_list: int):
    """Merge one list into another"""
    result = requests.post(f"{KANAPI_URL}lists/{source_list}/move",
                           json={'list_id': dest_list},
                           timeout=5)
    result.raise_for_status()


if __name__ == "__main__":
    app()
