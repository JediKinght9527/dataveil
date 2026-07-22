"""Gateway control commands: dv start / stop / status."""
from __future__ import annotations

import sys

import click
import uvicorn

from dv.config import get_settings
from dv.gateway.server import app


@click.command()
@click.option("--host", default=None, help="Bind host")
@click.option("--port", default=None, type=int, help="Bind port")
@click.option("--profile", default=None, help="Vault profile to use")
def start(host: str | None, port: int | None, profile: str | None):
    """Start the DataVeil gateway."""
    settings = get_settings()
    bind_host = host or settings.gateway_host
    bind_port = port or settings.gateway_port
    if profile:
        import os

        os.environ["DV_DEFAULT_PROFILE"] = profile

    click.echo(f"🔒 DataVeil Gateway starting at http://{bind_host}:{bind_port}")
    click.echo(f"   Profile: {profile or settings.default_profile}")
    click.echo(f"   Vault: {settings.vault_path}")
    click.echo(f"   Audit: {settings.audit_log_path}")
    uvicorn.run(app, host=bind_host, port=bind_port)


@click.command()
def stop():
    """Stop the DataVeil gateway (placeholder)."""
    click.echo("ℹ️  Gateway runs in foreground. Press Ctrl+C to stop.")


@click.command()
def status():
    """Show gateway status."""
    settings = get_settings()
    click.echo(f"Config vault: {settings.vault_path}")
    click.echo(f"Default profile: {settings.default_profile}")
    click.echo(f"Gateway endpoint: http://{settings.gateway_host}:{settings.gateway_port}")
    click.echo("Run 'dv start' to launch the gateway.")
