import flask
import flask_sqlalchemy
import datetime

# TODO ensure this is flask-restless-ng
import flask_restless

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/tmsql.db'
db = flask_sqlalchemy.SQLAlchemy(app)

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

def get_tasks_shortcuts(filters=None, sort=None, group_by=None, single=None, **kw):
    print(filters)
    # TODO default sort?
    # TODO get similar to task ID x
    # TODO search for string in name, desc, etc
    # TODO find triagable tasks
    # TODO find schedulable tasks
    # TODO find followupable tasks

def put_task_actions(resource_id=None, data=None, **kw):
    # TODO control some fields
    # TODO close
    # TODO duplicate
    pass

def post_task_new(data=None, **kw):
    # TODO any defaults?
    # TODO duplicate?
    pass

# TODO delete relationships only

db.create_all()

manager = flask_restless.APIManager(app, flask_sqlalchemy_db=db)

manager.create_api(Task,
                   methods=['GET', 'POST', 'PATCH'],
                   collection_name='tasks',
                   preprocessors={'GET_COLLECTION': [get_tasks_shortcuts],
                                  'PATCH_RESOURCE': [put_task_actions],
                                  'POST_RESOURCE': [post_task_new]})

app.run()
