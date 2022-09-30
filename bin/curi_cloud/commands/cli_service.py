import os
import click

from .utils import _add_deployment
from .utils import _add_service


@click.group(name="service")
def cli_service():
    pass


@cli_service.command("add", help="Create new service")
@click.option("--name", help="List of new service names, comma separated")
@click.option("--deployment", help="Name of deployment to create service in")
@click.pass_context
def add_service(ctx, deployment, name):
    deployment_dir = f'{ctx.obj["dir"]}/deployments'

    if not os.path.isdir(f"{deployment_dir}/{deployment}"):
        _add_deployment(deployment_dir, deployment)

    _add_service(deployment_dir, deployment, name)
