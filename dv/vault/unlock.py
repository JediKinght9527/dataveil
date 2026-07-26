"""Vault password resolution.

Resolution order (first hit wins):
1. ``DV_VAULT_PASSWORD`` environment variable
2. System keychain (macOS Keychain / Windows Credential Manager / Secret Service)

There is deliberately **no default password**. If no source yields a password,
callers must either prompt interactively or refuse to start.
"""

from __future__ import annotations

import os

from dv.config import Config
from dv.vault.keyring import get_keychain_password

ENV_VAR = "DV_VAULT_PASSWORD"


class VaultLockedError(RuntimeError):
    """Raised when no vault password source is available."""

    def __init__(self) -> None:
        super().__init__(
            "Vault password not available. Provide it via one of:\n"
            f"  1. Environment variable {ENV_VAR}\n"
            "  2. System keychain: dv vault save-password\n"
            "  3. Interactive prompt: run 'dv start' in a terminal"
        )


def resolve_vault_password(config: Config) -> str | None:
    """Resolve the vault password without prompting. Returns None if unavailable."""
    env_password = os.environ.get(ENV_VAR)
    if env_password:
        return env_password

    keychain_password = get_keychain_password(
        service=config.vault.keyring_service,
        account=config.vault.keyring_account,
    )
    if keychain_password:
        return keychain_password

    return None


def require_vault_password(config: Config) -> str:
    """Resolve the vault password or raise VaultLockedError. Never returns a default."""
    password = resolve_vault_password(config)
    if password is None:
        raise VaultLockedError()
    return password
