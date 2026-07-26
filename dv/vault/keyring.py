"""System keychain integration (macOS/Windows/Linux)."""

from typing import Optional


def get_keychain_password(service: str = "dataveil", account: str = "vault") -> Optional[str]:
    """Try to retrieve vault password from system keychain."""
    try:
        import keyring  # type: ignore[import-untyped]

        return keyring.get_password(service, account)
    except Exception:
        return None


def set_keychain_password(password: str, service: str = "dataveil", account: str = "vault") -> bool:
    """Store vault password in system keychain."""
    try:
        import keyring  # type: ignore[import-untyped]

        keyring.set_password(service, account, password)
        return True
    except Exception:
        return False
