"""TaskMaster non-JS WebGUI which fronts the RESTful API"""

import secrets
import datetime
import os
from flask import Flask, g, flash, session, request, render_template, redirect, url_for
import requests


KANAPI_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:29325/')
DEFAULT_CATEGORY = 1
KAN_LISTS = [3, 4, 5]
DATE_FMT = "%a %d %b"
INBOX_LIST_ID = 1


app = Flask(__name__)
app.secret_key = secrets.token_hex()


def get_cats():
    """Return all categories with their IDs"""
    result = requests.get(f"{KANAPI_URL}categories/",
                           timeout=1)
    result.raise_for_status()
    return result.json()


@app.get('/')
def stage_exec():
    """Display current tasks, either exec only or all"""
    contexts = get_cats()
    context = request.args.get('context')
    if context:
        flash(f'Context is now {context}')
        session['context'] = context
    else:
        context = session.get('context')
    if not context:
        # return render_template('contexts.html', contexts=contexts)
        context = DEFAULT_CATEGORY
    assert context in [c['category_id'] for c in contexts]
    all_lists = requests.get(f"{KANAPI_URL}lists/", timeout=1).json()
    tasks = [requests.get(f"{KANAPI_URL}/lists/{x}", timeout=1).json() for x in KAN_LISTS]
    return render_template('home.html',
                           tasks=tasks,
                           contexts=contexts,
                           context=context,
                           today=datetime.date.today().strftime(DATE_FMT),
                           all_lists=all_lists,
                           inbox=INBOX_LIST_ID)

@app.post('/tasks/<int:task_id>')
def modify_task(task_id):
    """Chage a given task"""
    # task = get_api().one_task(task_id)
    if request.form.get("complete"):
        res = requests.post(f"{KANAPI_URL}cards/{task_id}/close",
                            json={},
                            timeout=3)
        res.raise_for_status()
        flash(f"Completed task {task_id}")
    if request.form.get("priup") or request.form.get("pridn"):
        relative = 1
        if request.form.get("priup"):
            relative = -1
        orig_task = requests.get(f"{KANAPI_URL}cards/{task_id}").json()
        old_list_id = orig_task['list_id']
        assert old_list_id in KAN_LISTS
        old_idx = KAN_LISTS.index(old_list_id)
        new_idx = old_idx + relative
        assert new_idx >= 0
        assert new_idx <= len(KAN_LISTS)
        new_list_id = KAN_LISTS[new_idx]
        result = requests.post(f"{KANAPI_URL}cards/{task_id}/move",
                                json={'list_id': new_list_id},
                                timeout=3)
        flash(f"{task_id}: moved to list {new_list_id}")
    return redirect(url_for('stage_exec'))

@app.post('/tasks/')
def new_task():
    """Create a new task in this context active immediately"""
    # context = session.get('context')
    context = int(request.form.get('context'))
    name = request.form.get('name')
    assert name
    list_id = int(request.form.get('list_id'))
    result = requests.post(f"{KANAPI_URL}lists/{list_id}/cards/",
                        json={'card_name': name,
                              'category_id': context},
                        timeout=2)
    result.raise_for_status()
    flash(f"Created task {result.json()['card_id']}: {name}")
    return redirect(url_for('stage_exec'))

@app.get('/lists/<list_id>')
def one_list(list_id):
    tasks = requests.get(f"{KANAPI_URL}/lists/{list_id}", timeout=1).json()
    contexts = get_cats()
    return render_template('list.html',
                           tasks=tasks,
                           contexts=contexts)

