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
                           all_lists=all_lists)

@app.post('/tasks/<int:task_id>')
def modify_task(task_id):
    """Chage a given task"""
    task = get_api().one_task(task_id)
    if request.form.get("complete"):
        task.close()
        flash(f"Completed task {task_id}: {task.export()['name']}")
    if request.form.get("unstage"):
        task.warm(un=True)
        flash(f"Unstaged task {task_id}: {task.export()['name']}")
    if request.form.get("stage"):
        task.warm()
        flash(f"Staged task {task_id}: {task.export()['name']}")
    if request.form.get("push"):
        current_timeline = task.getsched()
        timelines = get_api().timelines_native()
        assert current_timeline
        assert timelines
        s1_date_raw = timelines[0]
        assert s1_date_raw > current_timeline
        s1_date = s1_date_raw.strftime(DATE_FMT)
        if len(timelines) > 1:
            s2_date = timelines[1].strftime(DATE_FMT)
        else:
            s2_date = None
        task.schedule(s1_date_raw)
        flash(f"Pushed task {task_id}: {task.export()['name']} to {s1_date}-{s2_date}")
    if request.form.get("priup") or request.form.get("pridn"):
        relative = -1
        if request.form.get("priup"):
            relative = 1
        _, old_letter, old_priority = task.prioritize()
        direction, new_letter, new_priority = task.prioritize(relative)
        message = "Same"
        if direction > 1:
            message = "Raised"
        elif direction < 1:
            message = "Lowered"
        flash(f"{message} priority {task_id}: {task.export()['name']} "
              f"from {old_letter}/{old_priority} to {new_letter}/{new_priority}")
    view_stage = None
    if request.form.get("mode") == "True":
        view_stage = "on"
    return redirect(url_for('stage_exec', stage=view_stage))

@app.post('/tasks/')
def new_task():
    """Create a new task in this context active immediately"""
    context = session.get('context')
    assert context
    name = request.form.get('name')
    assert name
    task = get_api().new_task({'context': context,
                               'name': name,
                               'wakeup': datetime.date.today().isoformat()})
    flash(f"Created task {task.tid}: {name}")
    return redirect(url_for('stage_exec', stage="on"))

@app.get('/lists/<list_id>')
def one_list(list_id):
    tasks = requests.get(f"{KANAPI_URL}/lists/{list_id}", timeout=1).json()
    contexts = get_cats()
    return render_template('list.html',
                           tasks=tasks,
                           contexts=contexts)

