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
    'priority': flask_restx.fields.Integer(description='Priority')
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


@taskns.route('/')
class TaskList(flask_restx.Resource):
    # TODO swagger document mode param
    @taskns.doc('list_tasks')
    @taskns.marshal_list_with(task)
    def get(self):
        parser = flask_restx.reqparse.RequestParser() # TODO better way to call this?
        parser.add_argument('mode', choices=('triage', 'schedule', 'stage', 'execute', 'all', 'open', 'closed'), default='open')
        args = parser.parse_args()
        mymo = args['mode']
        assert mymo
        if mymo == 'all':
            return Task.query.all()
        if mymo == 'open':
            return Task.query.filter_by(closed=None).all()
        if mymo == 'closed':
            return Task.query.filter(Task.closed != None).order_by(Task.closed.desc()).all()
        if mymo == 'execute':
            return Task.query.filter_by(warm=True, closed=None).order_by(Task.frog.desc(), Task.priority).all()
        if mymo == 'stage':
            # TODO should this include warm?
            return Task.query.filter(Task.closed == None, Task.wakeup <= datetime.datetime.now()).order_by(Task.frog.desc(), Task.priority, Task.urgent.desc(), Task.important.desc()).all()
        if mymo == 'schedule':
            # TODO also put in overdue
            # TODO should this include current schedule
            # TODO bulk reschedule option?
            return Task.query.filter(Task.closed == None, Task.warm == False, Task.wakeup == None).order_by(Task.important.desc(), Task.urgent.desc()).all()
        if mymo == 'triage':
            # TODO look for missing tags here
            return Task.query.filter(Task.closed == None, ((Task.pomodoros == None) | (Task.urgent == None) | (Task.important == None))).all()
        assert False

    @taskns.doc('create_task')
    @taskns.expect(task)
    @taskns.marshal_with(task, code=201)
    def post(self):
        # TODO restrict
        newtask = Task(**api.payload)
        db.session.add(newtask)
        db.session.commit()
        return newtask, 201


@taskns.route('/<int:id>')
@taskns.response(404, 'Task not found')
@taskns.param('id', 'Task ID')
class TodoOne(flask_restx.Resource):
    @taskns.doc('get_task')
    @taskns.marshal_with(task)
    def get(self, id):
        return Task.query.get_or_404(id)

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
        return mytask


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
            return [mytask, newtask]
        else:
            return [mytask]
        



# TODO get similar to task ID x
# TODO search for string in name, desc, etc
# TODO search for tags


db.create_all()


if __name__ == '__main__':
    app.run()
