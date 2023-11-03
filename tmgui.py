"""TaskMaster non-JS WebGUI which fronts the RESTful API"""

import secrets
import datetime
import os
from flask import Flask, g, flash, session, request, render_template, redirect, url_for
from tmclilib import TMApi

DATE_FMT = "%a %d %b"

app = Flask(__name__)
app.secret_key = secrets.token_hex()

def get_api():
    """Get TM Client object"""
    if 'api' not in g:
        g.api = TMApi(os.environ['TMAPIURL'])
    return g.api



@app.get('/')
def stage_exec():
    """Display current tasks, either exec only or all"""
    stage = (request.args.get('stage') == 'on')
    contexts = sorted(get_api().contexts())
    context = request.args.get('context')
    if context:
        flash(f'Context is now {context}')
        session['context'] = context
    else:
        context = session.get('context')
    if not context:
        return 'pick a context'
    assert context in contexts
    mode = 'stage' if stage else 'execute'
    pass_context = context if stage else None
    tasks = get_api().all_tasks(mode=mode, context=pass_context)
    task_extra = [task.export() for task in tasks]
    for task in task_extra:
        if task["due"]:
            task["due_date"] = datetime.datetime.fromisoformat(task["due"]).strftime(DATE_FMT)
        else:
            task["due_date"] = None
    timelines = get_api().timelines_native()
    if timelines:
        s1_date = timelines[0].strftime(DATE_FMT)
        if len(timelines) > 1:
            s2_date = timelines[1].strftime(DATE_FMT)
        else:
            s2_date = None
    else:
        s1_date = None
        s2_date = None
    return render_template('home.html',
                           tasks=task_extra,
                           contexts=contexts,
                           context=context,
                           today=datetime.date.today().strftime(DATE_FMT),
                           s1_date=s1_date,
                           s2_date=s2_date,
                           stage=stage)

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
