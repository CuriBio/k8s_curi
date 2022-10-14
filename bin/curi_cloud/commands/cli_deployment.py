import click

from .utils import _add_deployment


@click.group(name="deployment")
def cli_deployment():
    pass


@cli_deployment.command("new", help="Create new deployment")
@click.option("--name", help="Add new deployment")
@click.pass_context
def new_deployment(ctx, name):
    deployment_dir = f'{ctx.obj["dir"]}/deployments'
    _add_deployment(deployment_dir, name)
