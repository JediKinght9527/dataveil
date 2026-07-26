"""Gateway control commands: dv start / stop / status."""

from __future__ import annotations

import os
import sys

import click
import uvicorn

from dv.config import load_config
from dv.vault.unlock import ENV_VAR, resolve_vault_password


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
        os.environ["DV_DEFAULT_PROFILE"] = profile

    if bind_host not in ("127.0.0.1", "localhost"):
        click.echo(f"⚠️  Binding to {bind_host} exposes the gateway beyond this machine.")
        click.echo("   The gateway holds decrypted API keys — keep it on 127.0.0.1 unless")
        click.echo("   you fully control the network (e.g. inside a container).")

    # Resolve vault password before binding the port, so we fail fast and can
    # prompt interactively. Never fall back to a default password.
    if resolve_vault_password(config) is None:
        if sys.stdin.isatty():
            password = click.prompt("Vault password", hide_input=True)
            os.environ[ENV_VAR] = password
        else:
            click.echo("❌ No vault password available and not running in a terminal.")
            click.echo(f"   Set {ENV_VAR}, or store it in the system keychain with:")
            click.echo("   dv vault save-password")
            raise SystemExit(1)

    click.echo(f"🔒 DataVeil Gateway starting at http://{bind_host}:{bind_port}")
    click.echo(f"   Profile: {profile or config.gateway.default_profile}")
    click.echo(f"   Vault: {config.vault.path}")
    audit_desc = (
        f"enabled → {config.audit.log_path}" if config.audit.enabled else "disabled (default)"
    )
    click.echo(f"   Audit: {audit_desc}")
    uvicorn.run(app_import_string(), host=bind_host, port=bind_port)


def app_import_string():
    from dv.gateway.server import app

    return app


@click.command()
def stop():
    """Stop the DataVeil gateway (placeholder)."""
    click.echo("ℹ️  Gateway runs in foreground. Press Ctrl+C to stop.")


@click.command()
def status():
    """Show gateway status."""
    config = load_config()
    password_source = "not available"
    if os.environ.get(ENV_VAR):
        password_source = f"env ({ENV_VAR})"
    elif resolve_vault_password(config):
        password_source = "system keychain"
    click.echo(f"Config vault: {config.vault.path}")
    click.echo(f"Vault password source: {password_source}")
    click.echo(f"Default profile: {config.gateway.default_profile}")
    click.echo(f"Gateway endpoint: http://{config.gateway.host}:{config.gateway.port}")
    click.echo(f"Audit logging: {'enabled' if config.audit.enabled else 'disabled (default)'}")
    click.echo("Run 'dv start' to launch the gateway.")
