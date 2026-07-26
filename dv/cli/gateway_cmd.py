"""Gateway control commands: dv start / stop / status."""

from __future__ import annotations

import click
import uvicorn

from dv.config import load_config
from dv.gateway.server import app


@click.command()
@click.option("--host", default=None, help="Bind host")
@click.option("--port", default=None, type=int, help="Bind port")
@click.option("--profile", default=None, help="Vault profile to use")
def start(host: str | None, port: int | None, profile: str | None):
    """Start the DataVeil gateway."""
    config = load_config()
    bind_host = host or config.gateway.host
    bind_port = port or config.gateway.port
    if profile:
        import os

        os.environ["DV_DEFAULT_PROFILE"] = profile

    click.echo(f"🔒 DataVeil Gateway starting at http://{bind_host}:{bind_port}")
    click.echo(f"   Profile: {profile or config.gateway.default_profile}")
    click.echo(f"   Vault: {config.vault.path}")
    click.echo(f"   Audit: {config.audit.log_path}")
    uvicorn.run(app, host=bind_host, port=bind_port)


@click.command()
def stop():
    """Stop the DataVeil gateway (placeholder)."""
    click.echo("ℹ️  Gateway runs in foreground. Press Ctrl+C to stop.")


@click.command()
def status():
    """Show gateway status."""
    config = load_config()
    click.echo(f"Config vault: {config.vault.path}")
    click.echo(f"Default profile: {config.gateway.default_profile}")
    click.echo(f"Gateway endpoint: http://{config.gateway.host}:{config.gateway.port}")
    click.echo("Run 'dv start' to launch the gateway.")
