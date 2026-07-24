"""CLI entry point with Click."""
import click


@click.group()
@click.version_option(version="0.1.0", prog_name="dv")
def cli():
    """DataVeil — Privacy-first local gateway for LLM APIs."""
    pass


# Import subcommands
from dv.cli.gateway_cmd import start, status, stop  # noqa: E402
from dv.cli.init_cmd import init  # noqa: E402
from dv.cli.vault_cmd import vault  # noqa: E402

cli.add_command(vault)
cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(init)
