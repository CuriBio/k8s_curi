import click
import os

from commands.cli_service import cli_service
from commands.cli_deployment import cli_deployment

@click.group()
@click.argument('directory', type=click.Path(exists=True))
@click.pass_context
def main(ctx, directory):
    """
    Arguments:
        deployment: {string} - Repo directory
    """
    ctx.obj = {'dir': os.path.expanduser(directory)}

if __name__ == '__main__':
    main.add_command(cli_service)
    main.add_command(cli_deployment)
    main()
