"""Configuration commands (future)."""
import click


@click.group(name="config")
def config():
    """Manage DataVeil configuration."""
    pass
