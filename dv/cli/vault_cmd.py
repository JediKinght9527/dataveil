"""Vault management commands: dv vault add/list/rm/save-password."""

import click

from dv.config import load_config
from dv.vault.store import VaultStore


def _open_store(password: str) -> VaultStore:
    """Open the vault and verify the password against existing secrets."""
    config = load_config()
    store = VaultStore(db_path=config.vault.path, password=password)
    if not store.verify_password():
        raise click.ClickException("Wrong vault password (cannot decrypt existing secrets).")
    return store


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
    store = _open_store(password)

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
    store = _open_store(password)
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
    store = _open_store(password)
    if store.remove_key(profile):
        click.echo(f"🗑️  Profile '{profile}' removed.")
    else:
        click.echo(f"⚠️  Profile '{profile}' not found.")


@vault.command(name="save-password")
@click.password_option("--password", prompt="Vault password", confirmation_prompt=True)
def save_password(password: str):
    """Store the vault password in the system keychain (macOS/Windows/Linux)."""
    config = load_config()
    # Verify before saving so we never persist a wrong password.
    store = VaultStore(db_path=config.vault.path, password=password)
    if not store.verify_password():
        raise click.ClickException("Wrong vault password (cannot decrypt existing secrets).")

    from dv.vault.keyring import set_keychain_password

    if set_keychain_password(
        password,
        service=config.vault.keyring_service,
        account=config.vault.keyring_account,
    ):
        click.echo("✅ Vault password stored in system keychain.")
        click.echo("   'dv start' will now unlock the vault automatically.")
    else:
        raise click.ClickException(
            "Could not access the system keychain. Install the 'keyring' package: "
            "pip install keyring"
        )
