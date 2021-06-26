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

api = flask_restx.Api(app, version='0.1', title='TaskMaster API', description='API for interacting with a TaskMaster DB')

taskns = api.namespace('tasks', description='TODO operations')

# TODO add more fields
task = api.model('Task', {'id': flask_restx.fields.Integer(readonly=True, description='Task ID'),
    'name': flask_restx.fields.String(required=True, description='Short name of task'),
    'created':  flask_restx.fields.DateTime(readonly=True, description='When task created'),
    'closed': flask_restx.fields.DateTime(readonly=True, description='When task closed'),
    'updated': flask_restx.fields.DateTime(readonly=True, description='When task updated')
    })

action = api.model('Action', {'close': flask_restx.fields.Boolean(description='Close task', default=False), 'duplicate': flask_restx.fields.Boolean(description='Duplicate task', default=False)})


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    #priority ABC
    #urgent = db.Column(db.Boolean)
    #important = db.Column(db.Boolean)
    #frog = db.Column(db.Boolean)
    #pomodoros = db.Column(db.Integer)
    #wakeup = db.Column(db.DateTime)
    #description = db.Column(db.Text)
    #warm = db.Column(db.Boolean)
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

@taskns.route('/')
class TaskList(flask_restx.Resource):
    @taskns.doc('list_tasks')
    @taskns.marshal_list_with(task)
    def get(self):
        return Task.query.all()

    @taskns.doc('create_task')
    @taskns.expect(task)
    @taskns.marshal_with(task, code=201)
    def post(self):
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
        if 'name' in api.payload:
            mytask.name = api.payload['name']
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
# TODO find triagable tasks
# TODO find schedulable tasks
# TODO find followupable tasks


db.create_all()


if __name__ == '__main__':
    app.run()
