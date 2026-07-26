"""Vault management commands: dv vault add/list/rm."""

import click

from dv.config import load_config
from dv.vault.store import VaultStore


@click.group(name="vault")
def vault():
    """Manage encrypted API keys."""
    pass


@vault.command()
@click.option("--profile", required=True, help="Profile name (e.g. work, personal)")
@click.option("--provider", default="kimi", help="Provider: kimi, openai, anthropic")
@click.option("--base-url", default="", help="API base URL (auto-detected if empty)")
@click.password_option("--api-key", prompt="API Key", confirmation_prompt=False)
@click.password_option("--password", prompt="Vault password", confirmation_prompt=False)
def add(profile: str, provider: str, base_url: str, api_key: str, password: str):
    """Add an encrypted API key to the vault."""
    config = load_config()
    store = VaultStore(db_path=config.vault.path, password=password)

    if not base_url:
        from dv.vault.profile import DEFAULT_PROFILES

        if provider in DEFAULT_PROFILES:
            base_url = DEFAULT_PROFILES[provider].base_url
        else:
            raise click.BadParameter(f"Unknown provider: {provider}")

    store.add_key(profile, provider, base_url, api_key)
    click.echo(f"✅ Key for profile '{profile}' ({provider}) encrypted and stored.")


@vault.command(name="list")
@click.password_option("--password", prompt="Vault password", confirmation_prompt=False)
def list_keys(password: str):
    """List stored profiles."""
    config = load_config()
    store = VaultStore(db_path=config.vault.path, password=password)
    profiles = store.list_profiles()
    if not profiles:
        click.echo("No profiles found.")
        return
    click.echo("Stored profiles:")
    for p in profiles:
        click.echo(f"  • {p}")


@vault.command()
@click.option("--profile", required=True)
@click.password_option("--password", prompt="Vault password", confirmation_prompt=False)
def rm(profile: str, password: str):
    """Remove a profile from the vault."""
    config = load_config()
    store = VaultStore(db_path=config.vault.path, password=password)
    if store.remove_key(profile):
        click.echo(f"🗑️  Profile '{profile}' removed.")
    else:
        click.echo(f"⚠️  Profile '{profile}' not found.")
