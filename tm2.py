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
    return '{}\t{}\t{}\t{}\t{}'.format(exp['mode'].upper(),
                                       tsk.uif(),
                                       exp['pomodoros'],
                                       dateornull(tsk.getsched(), abbrev=True),
                                       exp['name'])

def taskchoice(objlist):
    """Given a list of task objects, show them and let a user pick one - return the object"""
    # TODO multiple
    # TODO search all
    # TODO allow "new"
    choices = [taskstr(x) for x in objlist]
    print(list(enumerate(choices)))
    choice = inquirer.list_input('pick a task', choices=[(x[1], x[0]) for x in enumerate(choices)])
    return objlist[choice]

def tupdate(taskobj, updatedct, confirm=True):
    """Update a task, optionally confirming choices"""
    if confirm:
        print(updatedct)
        choice = inquirer.confirm("Continue?", default=True)
        if not choice:
            return
    taskobj.update(updatedct)
    print(taskobj.export())

def triageone(tobj):
    """Triage one object"""
    # TODO current values as defaults
    questions = [inquirer.Confirm('important', message='Is it important?'),
                 inquirer.Confirm('urgent', message='Is it urgent?'),
                 inquirer.Text('pomodoros', message='How many poms?')] # TODO validate
    answers = inquirer.prompt(questions)
    answers['pomodoros'] = int(answers['pomodoros'])
    tupdate(tobj, answers)

def scheduleone(tobj):
    """Schedule one object"""
    currsched = tobj.getsched()
    newsched = datetime.datetime.fromisoformat(inquirer.text(message='date',
                                                             default=dateornull(currsched)))
    if currsched != newsched:
        # TODO confirm
        tobj.schedule(newsched)
    # TODO - second level - allow user to pick from a list:
    #           current schedule
    #           now
    #           plus 1 hour
    #           plus one day
    #           afternoon
    #           weekend
    #           weekday
    #           etc from each
    #   default: current or NOW, order by time
    #   then ask for hour specify; default is what is assoc with choice, or NULL
    # TODO - THIRD LEVEL -  pull common times



def mainloop(api, mode=None):
    """Loop through a single mode"""
    while True:
        tasklist = api.all_tasks(mode=mode)
        mychoice = taskchoice(tasklist)
        print(mychoice.export())

        # TODO take into account current status of the task itself to determine default
        action = inquirer.list_input('action',
                                     choices=['triage', 'schedule', 'stage', 'execute'],
                                     default=mode)

        if action == 'triage':
            triageone(mychoice)
        elif action == 'schedule':
            scheduleone(mychoice)
        elif action == 'stage':
            # TODO more intuitive warm/unwarm, confirm, etc
            mychoice.warm(un=mychoice.export()['warm'])
        elif action == 'execute':
            if inquirer.confirm('Close this task?'):
                # TODO duplicate, etc
                mychoice.close()
        else:
            assert False

        # TODO set priority/order
        # TODO set priority/order
        # TODO set Frog


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
        print(taskobj.export())

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
