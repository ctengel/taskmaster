#!/usr/bin/env python3

"""A basic CLI Client for TaskMaster"""

import click
import inquirer
import tmclilib


def dateornull(dateobj=None):
    """Return a brief representation of date time or blank"""
    # NOTE: not part of Task object since dates many places
    if not dateobj:
        return '   -   -  -  '
    return dateobj.strftime('%a-%b-%d-%H')

def taskchoice(objlist):
    """Given a list of task objects, show them and let a user pick one - return the object"""
    # TODO multiple
    choices = ['{}\t{}\t{}\t{}\t{}'.format(x.export()['mode'].upper(),
                                           x.uif(),
                                           x.export()['pomodoros'],
                                           dateornull(x.export()['wakeup']),
                                           x.export()['name']) for x in objlist]
    print(list(enumerate(choices)))
    choice = inquirer.list_input('pick a task', choices=[(x[1], x[0]) for x in enumerate(choices)])
    return objlist[choice]

@click.group()
@click.option('-a', '--api', default=False)
@click.pass_context
def cli(ctx, api):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    # TODO allow API URL to be stored in an environment variable
    ctx.obj['API'] = tmclilib.TMApi(url=api)

@cli.command()
@click.pass_context
def new(ctx):
    """Add a task from standard input"""
    # TODO allow specifying task on CLI
    while True:
        taskname = inquirer.text(message='task')
        taskobj = ctx.obj['API'].new_task({'name': taskname})
        print(taskobj.export())

# see #13
#@cli.command()
#@click.pass_context
#def import(ctx):
#    pass

@cli.command()
@click.pass_context
def triage(ctx):
    """Decide on importance, urgency, and duration of tasks"""
    while True:
        tasklist = ctx.obj['API'].all_tasks(mode='triage')
        mychoice = taskchoice(tasklist)
        print(mychoice.export())
        # TODO current values as defaults
        questions = [inquirer.Confirm('important', message='Is it important?'),
                     inquirer.Confirm('urgent', message='Is it urgent?'),
                     inquirer.Text('pomodoros', message='How many poms?')] # TODO validate
        answers = inquirer.prompt(questions)
        answers['pomodoros'] = int(answers['pomodoros'])
        mychoice.update(answers)
        print(mychoice.export())

@cli.command()
@click.pass_context
def schedule(ctx):
    """Determine when to begin a task"""
    while True:
        tasklist = ctx.obj['API'].all_tasks(mode='schedule')
        mychoice = taskchoice(tasklist)
        print(mychoice.export())
        currsched = mychoice.export()['wakeup']
        # TODO - first level - just specify a date spec (default is current)
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


@cli.command()
@click.pass_context
def stage(ctx):
    # TODO implement with #9
    pass

@cli.command()
@click.pass_context
def execute(ctx):
    # TODO implement with #9
    pass

# see #22
#@cli.command()
#@click.pass_context
#def print(ctx):
#    pass

# see #20
@cli.command()
@click.pass_context
def statusrep(ctx):
    pass


if __name__ == '__main__':
    cli(obj={})
