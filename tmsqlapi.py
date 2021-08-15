"""Task Master RESTful API to SQL database"""

import datetime
import flask
import flask_restx
import flask_sqlalchemy


# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/tmsql.db'
db = flask_sqlalchemy.SQLAlchemy(app)

api = flask_restx.Api(app, version='0.1', title='TaskMaster API', description='API for interacting with a TaskMaster DB')#, validate=True) TODO validate

taskns = api.namespace('tasks', description='TODO operations')

# TODO add more fields
task = api.model('Task', {'id': flask_restx.fields.Integer(readonly=True, description='Task ID'),
    'name': flask_restx.fields.String(required=True, description='Short name of task'),
    'created':  flask_restx.fields.DateTime(readonly=True, description='When task created'),
    'closed': flask_restx.fields.DateTime(readonly=True, description='When task closed'),
    'updated': flask_restx.fields.DateTime(readonly=True, description='When task updated'),
    'urgent': flask_restx.fields.Boolean(description='Eisenhower urgency'),
    'important': flask_restx.fields.Boolean(description='Eisenhower importance'),
    'frog': flask_restx.fields.Boolean(description='Is it a frog?'),
    'wakeup': flask_restx.fields.DateTime(description='When a task should be staged or slept until'),
    'warm': flask_restx.fields.Boolean(description='Actively in execution'),
    'pomodoros': flask_restx.fields.Integer(description='How long it take'),
    'priority': flask_restx.fields.Integer(description='Priority'),
    'mode': flask_restx.fields.String(readonly=True, description='Primary mode')
    })

action = api.model('Action', {'close': flask_restx.fields.Boolean(description='Close task', default=False), 'duplicate': flask_restx.fields.Boolean(description='Duplicate task', default=False)})


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    priority = db.Column(db.Integer)
    urgent = db.Column(db.Boolean)
    important = db.Column(db.Boolean)
    frog = db.Column(db.Boolean, default=False)
    pomodoros = db.Column(db.Integer)
    wakeup = db.Column(db.DateTime)
    #description = db.Column(db.Text)
    warm = db.Column(db.Boolean, default=False)  #TODO should this be nullable
    created = db.Column(db.DateTime, default=datetime.datetime.now)
    updated = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    closed = db.Column(db.DateTime)
    #url = db.Column(db.String(256))
    #assignee = db.Column(db.String(16))
    #source = db.Column(db.String(256))
    #context = db.Column(db.String(16))
    #project = db.Column(db.String(16))
    #goal = db.Column(db.String(16))
    #dependency_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    #nexttasks = db.relationship('Person')
    # TODO due??? handle overdue???


def taskmode(mytask, upper=None):
    """Determine mode field

    Also verify that it belongs in 'upper' mode list
    """
    assert upper in [None, 'all', 'open', 'triage', 'schedule', 'stage', 'execute', 'closed']
    mode = None
    if mytask.closed is not None:
        mode = 'closed'
        assert upper in [None, 'all', 'closed']
    elif mytask.warm == True:
        mode = 'warm'
        assert upper in [None, 'all', 'open', 'execute', 'stage', 'triage']
    elif mytask.wakeup and mytask.wakeup <= datetime.datetime.now():
        mode = 'awake'
        assert upper in [None, 'all', 'open', 'stage', 'triage']
    elif mytask.wakeup and mytask.wakeup > datetime.datetime.now():
        mode = 'asleep'
        assert upper in [None, 'all', 'open', 'triage']
    elif mytask.pomodoros is not None and mytask.urgent is not None and mytask.important is not None:
        mode = 'schedule'
        assert upper in [None, 'all', 'open', 'schedule', 'triage']
    else:
        mode = 'triage'
        assert upper not in ['stage', 'execute', 'closed']
    assert mode
    if not upper or upper == 'all':
        return mode
    if upper == 'closed':
        assert mode == 'closed'
    if upper == 'open':
        assert mode != 'closed'
    if upper == 'execute':
        assert mode == 'warm'
    if upper == 'stage':
        assert mode in ['warm', 'awake']
    if upper == 'schedule':
        assert mode in ['schedule', 'triage']
    if upper == 'triage':
        assert mode not in ['closed', 'schedule']
    return mode



def mode_one(mytask, upper=None):
    """Add mode field to one task"""
    onemode = taskmode(mytask, upper)
    onedict = dict(mytask.__dict__)
    onedict['mode'] = onemode
    return onedict

def mode_many(mytasks, upper=None):
    """Add mode field to many tasks"""
    return [mode_one(x, upper) for x in mytasks]


@taskns.route('/')
class TaskList(flask_restx.Resource):
    # TODO swagger document mode param
    @taskns.doc('list_tasks')
    @taskns.marshal_list_with(task)
    def get(self):
        parser = flask_restx.reqparse.RequestParser() # TODO better way to call this?
        # TODO document these options
        parser.add_argument('mode', choices=('triage', 'schedule', 'stage', 'execute', 'all', 'open', 'closed'), default='open')
        parser.add_argument('until', type=flask_restx.inputs.datetime_from_iso8601)
        # TODO support just date only
        # TODO support for status report "since"
        args = parser.parse_args()
        mymo = args['mode']
        assert mymo
        if mymo == 'all':
            return mode_many(Task.query.all(), 'all')
        if mymo == 'open':
            return mode_many(Task.query.filter_by(closed=None).all(), 'open')
        if mymo == 'closed':
            return mode_many(Task.query.filter(Task.closed != None).order_by(Task.closed.desc()).all(), 'closed')
        if mymo == 'execute':
            return mode_many(Task.query.filter_by(warm=True, closed=None).order_by(Task.frog.desc(), Task.priority).all(), 'execute')
        if mymo == 'stage':
            # TODO should this include warm?
            comprar = datetime.datetime.now()
            if args['until']:
                comprar = args['until']
            return mode_many(Task.query.filter(Task.closed == None, Task.wakeup <= comprar).order_by(Task.frog.desc(), Task.priority, Task.urgent.desc(), Task.important.desc()).all(), 'stage')
        if mymo == 'schedule':
            # TODO also put in overdue
            # TODO should this include current schedule
            # TODO bulk reschedule option?
            return mode_many(Task.query.filter(Task.closed == None, Task.warm == False, Task.wakeup == None).order_by(Task.important.desc(), Task.urgent.desc()).all(), 'schedule')
        if mymo == 'triage':
            # TODO look for missing tags here
            return mode_many(Task.query.filter(Task.closed == None, ((Task.pomodoros == None) | (Task.urgent == None) | (Task.important == None))).all(), 'triage')
        assert False

    @taskns.doc('create_task')
    @taskns.expect(task)
    @taskns.marshal_with(task, code=201)
    def post(self):
        # TODO restrict
        newtask = Task(**api.payload)
        db.session.add(newtask)
        db.session.commit()
        return mode_one(newtask), 201


@taskns.route('/<int:id>')
@taskns.response(404, 'Task not found')
@taskns.param('id', 'Task ID')
class TodoOne(flask_restx.Resource):
    @taskns.doc('get_task')
    @taskns.marshal_with(task)
    def get(self, id):
        return mode_one(Task.query.get_or_404(id))

    @taskns.doc('put_task')
    @taskns.expect(task)
    @taskns.marshal_with(task)
    def put(self, id):
        mytask = Task.query.get_or_404(id)
        for key, value in api.payload.items():
            if key in ['name', 'priority', 'urgent', 'important', 'frog', 'pomodoros', 'warm']:
                setattr(mytask, key, value)
            elif key in ['wakeup']: # TODO is this the best way?
                setattr(mytask, key, datetime.datetime.fromisoformat(value)) # TODO timezone?
            else:
                flask_restx.abort(403)
        db.session.commit()
        return mode_one(mytask)


@taskns.route('/<int:id>/action')
@taskns.response(404, 'Task not found')
@taskns.param('id', 'Task ID')
class TodoAction(flask_restx.Resource):
    @taskns.doc('action_task')
    @taskns.expect(action)
    @taskns.marshal_list_with(task)
    def post(self, id):
        mytask = Task.query.get_or_404(id)        
        # TODO does this API result make sense?
        newtask = None
        if api.payload.get('duplicate'):
            # TODO cleanup as part of #3
            newtask = Task(name=mytask.name)
            db.session.add(newtask)
        if api.payload.get('close'):
            mytask.closed = datetime.datetime.now()
        db.session.commit()
        if newtask:
            return [mode_one(mytask), mode_one(newtask)]
        else:
            return [mode_one(mytask)]
        



# TODO get similar to task ID x
# TODO search for string in name, desc, etc
# TODO search for tags


db.create_all()


if __name__ == '__main__':
    app.run()
