import secrets
import datetime
import os
from flask import Flask, g, flash, session, request, render_template, redirect, url_for
from tmclilib import TMApi

DATE_FMT = "%a %d %b"

app = Flask(__name__)
app.secret_key = secrets.token_hex()

def get_api():
    if 'api' not in g:
        g.api = TMApi(os.environ['TMAPIURL'])
    return g.api

@app.get('/')
def stage_exec():
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
    tasks = get_api().all_tasks(mode=mode)#, context=context)
    task_extra = [task.export() for task in tasks]
    for task in task_extra:
        if task["due"]:
            task["due_date"] = datetime.datetime.fromisoformat(task["due"]).strftime(DATE_FMT)
        else:
            task["due_date"] = None
    return render_template('home.html',
                           tasks=task_extra,
                           contexts=contexts,
                           context=context,
                           today=datetime.date.today().strftime(DATE_FMT))

@app.post('/tasks/<int:task_id>')
def modify_task(task_id):
    if request.form.get("complete"):
        flash(f"Completed task {task_id}")
    if request.form.get("unstage"):
        flash(f"Unstaged task {task_id}")
    return redirect(url_for('stage_exec'))
