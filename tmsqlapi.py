import flask
import flask_restx
import flask_sqlalchemy
import datetime

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/tmsql.db'
db = flask_sqlalchemy.SQLAlchemy(app)

api = flask_restx.Api(app, version='0.1', title='TaskMaster API', description='API for interacting with a TaskMaster DB')

taskns = api.namespace('tasks', description='TODO operations')

# TODO add more stuffs
task = api.model('Task', {'id': flask_restx.fields.Integer(readonly=True, description='Task ID'),
    'name': flask_restx.fields.String(required=True, description='Short name of task')
    })



class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    urgent = db.Column(db.Boolean)
    important = db.Column(db.Boolean)
    pomodoros = db.Column(db.Integer)
    wakeup = db.Column(db.DateTime)
    description = db.Column(db.Text)
    warm = db.Column(db.Boolean)
    created = db.Column(db.DateTime, default=datetime.datetime.now)
    updated = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    closed = db.Column(db.DateTime)
    url = db.Column(db.String(256))
    asignee = db.Column(db.String(16))
    source = db.Column(db.String(256))
    context = db.Column(db.String(16))
    project = db.Column(db.String(16))
    goal = db.Column(db.String(16))
    context = db.Column(db.String(256))
    dependency_id = db.Column(db.Integer, db.ForeignKey('task.id'))
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

#@taskns.route('/<int:id>')
#@taskns.response(404, 'Task not found')
#@taskns.param('id', 'Task ID')
#class TodoOne(Resource):
#    @taskns.doc('get_task)

# TODO default sort?
# TODO get similar to task ID x
# TODO search for string in name, desc, etc
# TODO find triagable tasks
# TODO find schedulable tasks
# TODO find followupable tasks

# TODO control some fields
# TODO close
# TODO duplicate

# TODO any defaults?
# TODO duplicate?

# TODO delete relationships only

db.create_all()

#manager = flask_restless.APIManager(app, flask_sqlalchemy_db=db)

#manager.create_api(Task,
#                   methods=['GET', 'POST', 'PATCH'],
#                   collection_name='tasks',
#                   preprocessors={'GET_COLLECTION': [get_tasks_shortcuts],
#                                  'PATCH_RESOURCE': [put_task_actions],
#                                  'POST_RESOURCE': [post_task_new]})

if __name__ == '__main__':
    app.run()
