"""Task Master RESTful API to SQL database"""

import datetime
import flask
import flask_restx
import flask_sqlalchemy

# Possible contexts
CTX = ['hmdy', 'hmed', 'wknw', 'hmfm', 'wkin', 'wkof', 'errd', 'trip', 'hmid', 'wkid']

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config.from_envvar('TMSQLAPI_SETTINGS', silent=True)
db = flask_sqlalchemy.SQLAlchemy(app)

api = flask_restx.Api(app, version='0.1', title='TaskMaster API', description='API for interacting with a TaskMaster DB')#, validate=True) TODO validate

taskns = api.namespace('tasks', description='TODO operations')
tmlnns = api.namespace('timelines', description='Timelines')
ctxns = api.namespace('contexts', description='Contexts')

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
    'mode': flask_restx.fields.String(readonly=True, description='Primary mode'),
    'context': flask_restx.fields.String(description='Where it can be done'),
    'due': flask_restx.fields.DateTime(description='When a task must be done')
    })

action = api.model('Action', {'close': flask_restx.fields.Boolean(description='Close task', default=False),
                              'duplicate': flask_restx.fields.Boolean(description='Duplicate task', default=False)})
timeline = api.model('Timeline', {'timeline': flask_restx.fields.DateTime(description='Timeline'),
                                  'count': flask_restx.fields.Integer(description='How many times it is used')})


class Task(db.Model):
    """Task table in database"""
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
    context = db.Column(db.String(8))
    #project = db.Column(db.String(16))
    #goal = db.Column(db.String(16))
    #dependency_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    #nexttasks = db.relationship('Person')
    due = db.Column(db.DateTime)

def taskmode(mytask, upper=None, fut=None):
    """Determine mode field

    Also verify that it belongs in 'upper' mode list
    """
    if not fut:
        fut = datetime.datetime.now()
    assert upper in [None, 'all', 'open', 'triage', 'schedule', 'stage', 'execute', 'closed']
    mode = None
    if mytask.closed is not None:
        mode = 'closed'
        assert upper in [None, 'all', 'closed']
    elif mytask.due and mytask.due < fut:
        mode = 'overdue'
    elif mytask.warm == True:
        mode = 'warm'
        assert upper in [None, 'all', 'open', 'execute', 'stage', 'triage']
    elif mytask.wakeup and mytask.wakeup <= fut:
        mode = 'awake'
        assert upper in [None, 'all', 'open', 'stage', 'triage']
    elif mytask.wakeup and mytask.wakeup > fut:
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
        assert mode in ['warm', 'overdue']
    if upper == 'stage':
        assert mode in ['warm', 'awake', 'overdue']
    if upper == 'schedule':
        assert mode in ['schedule', 'triage', 'overdue']
    if upper == 'triage':
        assert mode not in ['closed', 'schedule']
    return mode



def mode_one(mytask, upper=None, fut=None):
    """Add mode field to one task"""
    onemode = taskmode(mytask, upper, fut=fut)
    onedict = dict(mytask.__dict__)
    onedict['mode'] = onemode
    return onedict

def mode_many(mytasks, upper=None, fut=None):
    """Add mode field to many tasks"""
    return [mode_one(x, upper, fut=fut) for x in mytasks]

def modesort(itema):
    """Return a numerical value for the mode of the task"""
    if itema['mode'] == 'overdue':
        return (0, None, None)
    if itema['mode'] == 'warm':
        return (1, not itema['urgent'], not itema['important'])
    if itema['mode'] == 'awake':
        return (2, not itema['urgent'], not itema['important'])
    if itema['mode'] == 'asleep':
        return (3, itema['wakeup'], None)
    # triage, schedule, etc
    return (4, None, None)

@taskns.route('/')
class TaskList(flask_restx.Resource):
    """All tasks API"""

    # TODO swagger document mode param
    @taskns.doc('list_tasks')
    @taskns.marshal_list_with(task)
    def get(self):
        """Get all tasks"""
        parser = flask_restx.reqparse.RequestParser() # TODO better way to call this?
        # TODO document these options
        parser.add_argument('mode', choices=('triage', 'schedule', 'stage', 'execute', 'all', 'open', 'closed', 'paper'), default='open')
        parser.add_argument('until', type=flask_restx.inputs.datetime_from_iso8601)
        parser.add_argument('search')
        parser.add_argument('context')
        # TODO support just date only
        # TODO support for status report "since"
        args = parser.parse_args()
        mymo = args['mode']
        assert mymo
        if args.get('context'):
            assert args['context'] in CTX
            assert mymo in ('paper', 'stage')
        if args.get('search'):
            # TODO integrate search better into the other modes
            assert mymo in ('all', 'open')
            if mymo == 'all':
                return mode_many(Task.query.filter(Task.name.like("%{}%".format(args['search']))).all(), 'all')
            else:
                return mode_many(Task.query.filter(Task.closed == None, Task.name.like("%{}%".format(args['search']))).all(), 'open')
        if mymo == 'all':
            return mode_many(Task.query.all(), 'all')
        if mymo == 'open':
            return mode_many(Task.query.filter_by(closed=None).all(), 'open')
        if mymo == 'closed':
            return mode_many(Task.query.filter(Task.closed != None).order_by(Task.closed.desc()).all(), 'closed')
        if mymo == 'execute':
            # TODO accept a context? or warm stays warm always?
            return mode_many(Task.query.filter_by(warm=True, closed=None).order_by(Task.frog.desc(), Task.priority.desc()).all(), 'execute')
        if mymo == 'stage':
            # TODO should this include warm?
            comprar = datetime.datetime.now()
            if args['until']:
                comprar = args['until']
            if args['context']:
                mtl = Task.query.filter(Task.closed == None,
                                        Task.context == args['context'],
                                        Task.wakeup <= comprar).order_by(Task.frog.desc(),
                                                                         Task.priority.desc(),
                                                                         Task.urgent.desc(),
                                                                         Task.important.desc()).all()
            else:
                mtl = Task.query.filter(Task.closed == None,
                                        Task.wakeup <= comprar).order_by(Task.frog.desc(),
                                                                         Task.priority.desc(),
                                                                         Task.urgent.desc(),
                                                                         Task.important.desc()).all()
            return mode_many(mtl, 'stage', fut=comprar)
        if mymo == 'paper':
            comprar = datetime.datetime.now() + datetime.timedelta(days=1)
            if args['until']:
                comprar = args['until']
            if args['context']:
                baselist = mode_many(Task.query.filter(Task.closed == None,
                                                       ((Task.wakeup == None) | (Task.wakeup <= comprar)),
                                                       ((Task.context == None) | (Task.context == args['context']) | (Task.due <= comprar))).order_by(Task.wakeup).all(),
                                     None)
                baselist.sort(key=modesort)
                return baselist                
            # TODO add a "paper" "upper"                
            baselist = mode_many(Task.query.filter(Task.closed == None,
                                                   ((Task.wakeup == None) | (Task.wakeup <= comprar))).order_by(Task.wakeup).all(),
                                 None)
            baselist.sort(key=modesort)
            return baselist
        if mymo == 'schedule':
            # TODO also put in overdue
            # TODO should this include current schedule
            # TODO allow context filter?
            return mode_many(Task.query.filter(Task.closed == None,
                                               Task.warm == False,
                                               Task.wakeup == None).order_by(Task.important.desc(),
                                                                             Task.urgent.desc()).all(),
                             'schedule')
        if mymo == 'triage':
            # TODO look for missing tags here, especially context
            return mode_many(Task.query.filter(Task.closed == None,
                                               ((Task.pomodoros == None) | (Task.urgent == None) | (Task.important == None))).all(),
                             'triage')
        assert False

    @taskns.doc('create_task')
    @taskns.expect(task)
    @taskns.marshal_with(task, code=201)
    def post(self):
        """Create task"""
        # TODO restrict
        indict = dict(api.payload)
        # TODO merge with PUT code
        if indict.get('wakeup'):
            indict['wakeup'] = datetime.datetime.fromisoformat(indict['wakeup'])
        if indict.get('due'):
            indict['due'] = datetime.datetime.fromisoformat(indict['due'])
        if indict.get('due') and indict.get('wakeup'):
            assert indict['wakeup'] < indict['due']
        if indict.get('context') is not None:
            assert indict['context'] in CTX
        newtask = Task(**indict)
        db.session.add(newtask)
        db.session.commit()
        return mode_one(newtask), 201


@taskns.route('/<int:id>')
@taskns.response(404, 'Task not found')
@taskns.param('id', 'Task ID')
class TodoOne(flask_restx.Resource):
    """One task API"""

    @taskns.doc('get_task')
    @taskns.marshal_with(task)
    def get(self, id):
        """Get one task"""
        return mode_one(Task.query.get_or_404(id))

    @taskns.doc('put_task')
    @taskns.expect(task)
    @taskns.marshal_with(task)
    def put(self, id):
        """Update one task"""
        # TODO should this be PATCH?
        mytask = Task.query.get_or_404(id)
        for key, value in api.payload.items():
            if key in ['name', 'priority', 'urgent', 'important', 'frog', 'pomodoros', 'warm']:
                setattr(mytask, key, value)
            elif key in ['wakeup', 'due']: # TODO is this the best way?
                setattr(mytask, key, datetime.datetime.fromisoformat(value)) # TODO timezone?
                # TODO keeping this seperate in case above used to deal with other timelike attributes
                if key == 'wakeup' and datetime.datetime.fromisoformat(value) > datetime.datetime.now():
                    mytask.warm = False
            elif key == 'context':
                assert value in CTX
                mytask.context = value
            else:
                flask_restx.abort(403)
        if mytask.due and mytask.wakeup:
            assert mytask.due > mytask.wakeup
        db.session.commit()
        return mode_one(mytask)


@taskns.route('/<int:id>/action')
@taskns.response(404, 'Task not found')
@taskns.param('id', 'Task ID')
class TodoAction(flask_restx.Resource):
    """API to take action on a task"""

    @taskns.doc('action_task')
    @taskns.expect(action)
    @taskns.marshal_list_with(task)
    def post(self, id):
        """Close and/or duplicate a task"""
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


@tmlnns.route('/')
class TimelineList(flask_restx.Resource):
    """List of timelines"""

    @taskns.doc('list_timelines')
    @taskns.marshal_list_with(timeline)
    def get(self):
        """Auto-generated timeline list"""
        # TODO show timelines per context (i.e. take a ctx arg and show what timelines are in that context only)
        # TODO allow listing due timelines
        parser = flask_restx.reqparse.RequestParser()# TODO better way to call this?
        # TODO document these options
        parser.add_argument('type', choices=('wakeup',), default='wakeup') # TODO - allow this to be all and then spec in results
        args = parser.parse_args()
        assert args['type'] == 'wakeup'
        result = Task.query.with_entities(Task.wakeup,
                                          db.func.count(Task.wakeup)).group_by(Task.wakeup).filter(Task.closed == None,
                                                                                                   Task.wakeup >= datetime.datetime.now()).order_by(db.func.count(Task.wakeup).desc()).all()
        return [{'timeline': x[0], 'count': x[1]} for x in result]


@ctxns.route('/')
class ContextList(flask_restx.Resource):
    """List of contexts"""

    @ctxns.doc('list_contexts')
    def get(self):
        return CTX

# TODO get similar to task ID x
# TODO search for string in name, desc, etc
# TODO search for tags


db.create_all()


if __name__ == '__main__':
    app.run()
