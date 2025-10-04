#!/usr/bin/env python3
"""Client for KanBan API"""

import os
import requests
import typer

KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')


app = typer.Typer()

@app.command()
def list_(list_id: int, context_id: int = None, tabbed: bool = False, csv_: bool = False):
    """List all cards in a given list"""
    result = requests.get(f"{KANAPI_URL}lists/{list_id}", timeout=1).json()
    print(result['list_name'])
    for card in result['cards']:
        print(card['card_name'])


if __name__ == "__main__":
    app()
