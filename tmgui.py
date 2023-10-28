import secrets
import os
from flask import Flask, g, flash, session, request
from tmclilib import TMApi

app = Flask(__name__)
app.secret_key = secrets.token_hex()

def get_api():
    if 'api' not in g:
        g.api = TMApi(os.environ['TMAPIURL'])
    return g.api

@app.route('/')
def stage_exec():
    stage = (request.args.get('stage') == 'on')
    context = request.args.get('context')
    if context:
        session['context'] = context
    else:
        context = session.get('context')
    if not context:
        return 'pick a context'
    mode = 'stage' if stage else 'execute'
    tasks = get_api().all_tasks(mode=mode, context=context)
    return render_template('task_list.html', tasks=[task.export() for task in tasks])

