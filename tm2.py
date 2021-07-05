#!/usr/bin/env python3

import click
import inquirer
import tmclilib

def taskchoice(objlist):
    # TODO multiple
    choices = ['{}\t{}'.format(x.export()['mode'].upper(), x.export()['name']) for x in objlist]
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

    ctx.obj['API'] = tmclilib.TMApi(url=api)

@cli.command()
@click.pass_context
def new(ctx):
    while True:
        taskname = inquirer.text(message='task')
        taskobj = ctx.obj['API'].new_task({'name': taskname})
        print(taskobj.export())

#@cli.command()
#@click.pass_context
#def import(ctx):
#    pass

@cli.command()
@click.pass_context
def triage(ctx):
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
    pass

@cli.command()
@click.pass_context
def stage(ctx):
    pass

@cli.command()
@click.pass_context
def execute(ctx):
    pass

#@cli.command()
#@click.pass_context
#def print(ctx):
#    pass

@cli.command()
@click.pass_context
def statusrep(ctx):
    pass


if __name__ == '__main__':
    cli(obj={})
