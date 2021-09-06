#!/usr/bin/env python3

"""A basic CLI Client for TaskMaster"""

import datetime
import click
import inquirer
import tmclilib


def dateornull(dateobj=None, abbrev=False):
    """Return a brief representation of date time or blank"""
    # NOTE: not part of Task object since dates many places
    if abbrev:
        if not dateobj:
            return '   -   -  -  '
        return dateobj.strftime('%a-%b-%d-%H')
    if not dateobj:
        return None
    return dateobj.isoformat()

def taskstr(tsk):
    """String representation of a task"""
    exp = tsk.export()
    return '{: <8}  {}  {: >4}  {}  {}'.format(exp['mode'].upper(),
                                       tsk.uif(),
                                       str(exp['pomodoros']),
                                       dateornull(tsk.getsched(), abbrev=True),
                                       exp['name'])

def taskchoice(objlist):
    """Given a list of task objects, show them and let a user pick one - return the object"""
    # TODO multiple
    # TODO search all
    # TODO allow "new"
    # TODO allow exit
    choices = [taskstr(x) for x in objlist]
    # TODO default=next one
    choice = inquirer.checkbox('pick a task',
                               choices=[(x[1], x[0]) for x in enumerate(choices)])
    return [objlist[x] for x in choice]

def tupdate(taskobj, updatedct, confirm=True):
    """Update a task, optionally confirming choices"""
    if confirm:
        print(updatedct)
        choice = inquirer.confirm("Continue?", default=True)
        if not choice:
            return
    taskobj.update(updatedct)
    #print(taskobj.export())

def triageone(tobj):
    """Triage one object"""
    # TODO current values as defaults
    questions = [inquirer.Confirm('important', message='Is it important?'),
                 inquirer.Confirm('urgent', message='Is it urgent?'),
                 inquirer.Text('pomodoros', message='How many poms?')] # TODO validate
    answers = inquirer.prompt(questions)
    answers['pomodoros'] = int(answers['pomodoros'])
    for tsk in tobj:
        tupdate(tsk, answers)

def scheduleone(tobj):
    """Schedule one object"""
    currsched = None
    if len(tobj) == 1:
        currsched = tobj[0].getsched()
    # TODO  pull common times - see #36
    # TODO add weekend, weekday, etc
    # TODO saner defaults and options (i.e. don't suggest this afternoon if already begun)
    # TODO friendlier display of options - see https://github.com/magmax/python-inquirer/blob/master/examples/list_tagged.py
    options = [None,
               currsched,
               datetime.datetime.now(),
               datetime.datetime.now() + datetime.timedelta(hours=1),
               datetime.date.today(),
               datetime.datetime.combine(datetime.date.today(),
                                         datetime.time(hour=12)),
               datetime.date.today() + datetime.timedelta(days=1),
               datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1),
                                         datetime.time(hour=6))]
    newsched = inquirer.list_input('date', choices=options, carousel=True)
    if not newsched:
        # TODO ask again if not valid
        # TODO allow date only
        newsched = datetime.datetime.fromisoformat(inquirer.text(message='date',
                                                                 default=dateornull(currsched)))
    if not isinstance(newsched, datetime.datetime):
        newsched = datetime.datetime.combine(newsched,
                                             datetime.time.fromisoformat(inquirer.text(message='time')))
    for tsk in tobj:
        if tsk.getsched() != newsched:
            # TODO confirm
            tsk.schedule(newsched)


def taskact(mychoice, default=None):
    """Given an existing task object, let the user do something

    Allows multiple actions until cancel
    """
    while True:
        for tsk in mychoice:
            print(tsk.export())

        # TODO take into account current status of the task itself to determine default
        action = inquirer.list_input('action',
                                     choices=['triage', 'schedule', 'stage', 'execute', 'modify', 'exit'],
                                     default=default,
                                     carousel=True)

        if action == 'triage':
            triageone(mychoice)
            default = 'schedule'
        elif action == 'schedule':
            scheduleone(mychoice)
            default = 'exit'
        elif action == 'stage':
            # TODO more intuitive warm/unwarm, confirm, etc
            base = None
            for tsk in mychoice:
                if base is None:
                    base = tsk.export()['warm']
                elif base != tsk.export()['warm']:
                    print('Can only stage or unstage, not both')
            for tsk in mychoice:
                tsk.warm(un=base)
            default = 'exit'
        elif action == 'execute':
            if inquirer.confirm('Close this task?'):
                for tsk in mychoice:
                    # TODO duplicate, etc
                    tsk.close()
                return
        elif action == 'exit':
            return
        elif action == 'modify':
            assert len(mychoice) == 1
            tsk = mychoice[0]
            newname = inquirer.text(message='New name:', default=tsk.export()['name'])
            tupdate(tsk, {'name': newname})
            return
        else:
            assert False

        # TODO set priority/order
        # TODO set Frog


def mainloop(api, mode=None):
    """Loop through a single mode"""
    while True:
        tasklist = api.all_tasks(mode=mode)
        mychoice = taskchoice(tasklist)
        taskact(mychoice, mode)


@click.group()
@click.option('-a', '--api', default=False)
@click.pass_context
def cli(ctx, api):
    """Click CLI parent object, setup API obj"""
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    # TODO allow API URL to be stored in an environment variable
    assert api
    ctx.obj['API'] = tmclilib.TMApi(url=api)

@cli.command()
@click.pass_context
@click.option('-f', '--file', type=click.File())
@click.option('-w',  '--wakeup')
@click.argument('task', nargs=-1)
def new(ctx, file, wakeup, task):
    """Add a task from standard input"""
    assert not (task and file)
    if not (task or file):
        assert not wakeup
    # TODO wakeup as datetime not string
    if file:
        # TODO more enhanced file analysis
        for one in file:
            taskobj = ctx.obj['API'].new_task({'name': one.strip(), 'wakeup': wakeup})
            print(taskobj.export())
        return
    if task:
        taskobj = ctx.obj['API'].new_task({'name': ' '.join(task), 'wakeup': wakeup})
        print(taskobj.export())
        return
    while True:
        taskname = inquirer.text(message='task')
        taskobj = ctx.obj['API'].new_task({'name': taskname})
        taskact([taskobj], 'triage')

# see #48
#@cli.command()
#@click.pass_context
#def reimport(ctx):
#    pass

@cli.command()
@click.pass_context
def triage(ctx):
    """Decide on importance, urgency, and duration of tasks"""
    mainloop(ctx.obj['API'], mode='triage')

@cli.command()
@click.pass_context
def schedule(ctx):
    """Determine when to begin a task"""
    mainloop(ctx.obj['API'], mode='schedule')

@cli.command()
@click.pass_context
def stage(ctx):
    """Prep tasks for execution"""
    mainloop(ctx.obj['API'], mode='stage')

@cli.command()
@click.pass_context
def execute(ctx):
    """Close tasks"""
    mainloop(ctx.obj['API'], mode='execute')


@cli.command()
@click.pass_context
@click.option('-u', '--until')
# TODO allow actual direct to printer
# TODO allow other modes besides stage
def paper(ctx, until):
    """Noninteractive printable list of tasks"""
    utl = None
    if until:
        utl = datetime.datetime.fromisoformat(until)
    tasklist = ctx.obj['API'].all_tasks(mode='stage', until=utl)
    for tsk in tasklist:
        print(taskstr(tsk))

# see #20
#@cli.command()
#@click.pass_context
#def statusrep(ctx):
#    pass


# TODO all tasks or open tasks loop

if __name__ == '__main__':
    cli(obj={})
