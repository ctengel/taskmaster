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
    return '{: <8} {: <4} {} {: >2} {} {} {}'.format(exp['mode'].upper(),
                                                     exp['context'].upper(),
                                                     tsk.uif(),
                                                     str(exp['pomodoros']),
                                                     dateornull(tsk.getsched(), abbrev=True),
                                                     dateornull(tsk.getsched(), abbrev=True),
                                                     exp['name'])

def taskchoice(objlist, new_opt=False, api_obj=None, new_def=None):
    """Given a list of task objects, show them and let a user pick one - return the object

    Set new_opt = True to allow a new task to be specified
    """
    # TODO search all
    # TODO allow "new"
    # TODO allow exit
    choices = [taskstr(x) for x in objlist]
    if new_opt:
        assert api_obj
        choices.append('NEW')
    # TODO default=next one
    choice = inquirer.checkbox('pick a task',
                               choices=[(x[1], x[0]) for x in enumerate(choices)])
    if new_opt and len(choices) - 1 in choice:
        assert len(choice) == 1
        taskname = inquirer.text(message='task', default=new_def)
        if not taskname:
            return []
        newtask = api_obj.new_task({'name': taskname})
        return [newtask]
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
                 inquirer.Text('pomodoros', message='How many poms?'),
                 inquirer.List('context', message='Which context?', choices=tobj[0].api.contexts())] # TODO validate
    answers = inquirer.prompt(questions)
    answers['pomodoros'] = int(answers['pomodoros'])
    print(answers)
    choice = inquirer.confirm("Continue?", default=True)
    if not choice:
        return
    for tsk in tobj:
        tupdate(tsk, answers, confirm=False)

def scheduleone(tobj):
    """Schedule one object"""
    currsched = None
    if len(tobj) == 1:
        currsched = tobj[0].getsched()
    # TODO  pull common times - see #36
    # TODO add weekend, weekday, etc
    # TODO saner defaults and options (i.e. don't suggest this afternoon if already begun)
    # TODO friendlier display of options
    #      see https://github.com/magmax/python-inquirer/blob/master/examples/list_tagged.py
    commontl  = tobj[0].api.timelines()
    options = [None,
               currsched
               ] + commontl + [
               datetime.datetime.now(),
               datetime.datetime.now() + datetime.timedelta(hours=1),
               datetime.date.today()]
    after_breakfast = datetime.datetime.combine(datetime.date.today(),
                                                datetime.time(hour=12))
    if after_breakfast > datetime.datetime.now():
        options.append(after_breakfast)
    options += [datetime.date.today() + datetime.timedelta(days=1),
                datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1),
                                          datetime.time(hour=6))]
    # TODO use date or null here?
    opt_lab = [("{} {}".format(x.strftime('%a'), x), x) if x else ("Custom", None)
               for x in options]
    newsched = inquirer.list_input('date', choices=opt_lab, carousel=True)
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
    choice = inquirer.confirm("Do you want to assign/reset a due date?", default=True)
    if not choice:
        return
    newdue = datetime.date(inquirer.text(message='date'))
    newdue = datetime.datetime.combine(newdue, datetime.time(hour=0))
    for tsk in tobj:
        if tsk.get_due() != newdue:
            tsk.set_due(newdue)



def taskact(mychoice, default=None):
    """Given an existing task object, let the user do something

    Allows multiple actions until cancel
    """
    while True:
        for tsk in mychoice:
            print(tsk.export())

        # TODO take into account current status of the task itself to determine default
        action = inquirer.list_input('action',
                                     choices=['triage',
                                              'schedule',
                                              'stage',
                                              'execute',
                                              'modify',
                                              'exit'],
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


def mainloop(api, mode=None, until=None, context=None):
    """Loop through a single mode"""
    if until:
        until = datetime.datetime.fromisoformat(until)
    while True:
        tasklist = api.all_tasks(mode=mode, until=until, context=context)
        mychoice = taskchoice(tasklist, new_opt=True, api_obj=api)
        if not mychoice:
            return
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
@click.option('-w', '--wakeup')
@click.option('-c', '--context')
@click.argument('task', nargs=-1)
def new(ctx, file, wakeup, task, context):
    """Add a task from standard input"""
    assert not (task and file)
    if not (task or file):
        assert not wakeup
    # TODO wakeup as datetime not string
    if file:
        # TODO more enhanced file analysis
        for one in file:
            taskobj = ctx.obj['API'].new_task({'name': one.strip(), 'wakeup': wakeup, 'context': context})
            print(taskobj.export())
        return
    if task:
        taskobj = ctx.obj['API'].new_task({'name': ' '.join(task), 'wakeup': wakeup, 'context': context})
        print(taskobj.export())
        return
    while True:
        taskname = inquirer.text(message='task')
        if not taskname:
            return
        taskobj = ctx.obj['API'].new_task({'name': taskname, 'context': context})
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
@click.option('-u', '--until',
              help='See future tasks')
@click.option('-c', '--context')
def stage(ctx, until, context):
    """Prep tasks for execution"""
    mainloop(ctx.obj['API'], mode='stage', until=until, context=context)

@cli.command()
@click.pass_context
def execute(ctx):
    """Close tasks"""
    mainloop(ctx.obj['API'], mode='execute')

@cli.command()
@click.pass_context
def all_tasks(ctx):
    """Interact with all tasks, including closed"""
    mainloop(ctx.obj['API'], mode='all')

@cli.command()
@click.pass_context
@click.option('-u', '--until',
              help='Period to show tasks over; only valid for default/paper and stage mode')
@click.option('-m',
              '--mode',
              type=click.Choice(['triage',
                                 'schedule',
                                 'stage',
                                 'execute',
                                 'all',
                                 'open',
                                 'closed',
                                 'paper']),
              default='paper',
              help='Show a different set of tasks',
              show_default=True)
@click.option('-c', '--context')
def paper(ctx, until, mode, context):
    """Noninteractive printable list of tasks

    Note this can be printed via lpr, etc
    """
    utl = None
    if until:
        utl = datetime.datetime.fromisoformat(until)
    if utl:
        assert mode in ('paper', 'stage')
    tasklist = ctx.obj['API'].all_tasks(mode=mode, until=utl, context=context)
    for tsk in tasklist:
        print(taskstr(tsk))

@cli.command()
@click.pass_context
@click.argument('task', nargs=-1, required=True)
def search(ctx, task):
    """Search for a task and allow wakeup or creation (aka upsert)"""
    srch_str = " ".join(task)
    tasklist = ctx.obj['API'].search_tasks(task_search=srch_str)
    mychoice = taskchoice(tasklist, new_opt=True, api_obj=ctx.obj['API'], new_def=srch_str)
    taskact(mychoice, 'schedule')

# see #20
#@cli.command()
#@click.pass_context
#def statusrep(ctx):
#    pass


# TODO all tasks or open tasks loop

if __name__ == '__main__':
    cli(obj={})
