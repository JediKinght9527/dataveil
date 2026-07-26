"""Tests for vault password resolution (no default password, fail closed)."""

import pytest

from dv.config import ConfigLoader
from dv.vault.store import VaultStore
from dv.vault.unlock import (
    ENV_VAR,
    VaultLockedError,
    require_vault_password,
    resolve_vault_password,
)


@pytest.fixture
def config(monkeypatch, tmp_path):
    # Isolate from the developer's real global config and env
    monkeypatch.delenv(ENV_VAR, raising=False)
    loader = ConfigLoader()
    loader.DEFAULT_CONFIG_PATH = tmp_path / "config.yaml"
    return loader.load(project_root=tmp_path)


class TestResolveVaultPassword:
    def test_env_var_wins(self, config, monkeypatch):
        monkeypatch.setenv(ENV_VAR, "from-env")
        assert resolve_vault_password(config) == "from-env"

    def test_keychain_fallback(self, config, monkeypatch):
        import dv.vault.unlock as unlock

        monkeypatch.setattr(unlock, "get_keychain_password", lambda **_: "from-keychain")
        assert resolve_vault_password(config) == "from-keychain"

    def test_no_source_returns_none(self, config, monkeypatch):
        import dv.vault.unlock as unlock

        monkeypatch.setattr(unlock, "get_keychain_password", lambda **_: None)
        assert resolve_vault_password(config) is None

    def test_require_raises_without_source(self, config, monkeypatch):
        import dv.vault.unlock as unlock

        monkeypatch.setattr(unlock, "get_keychain_password", lambda **_: None)
        with pytest.raises(VaultLockedError):
            require_vault_password(config)

    def test_no_default_password_anywhere(self, config, monkeypatch):
        """Regression: the old code fell back to keyring_account ('vault') as password."""
        import dv.vault.unlock as unlock

        monkeypatch.setattr(unlock, "get_keychain_password", lambda **_: None)
        result = resolve_vault_password(config)
        assert result != "vault"
        assert result != "changeme"
        assert result is None


class TestVerifyPassword:
    def test_empty_vault_accepts_any_password(self, tmp_path):
        store = VaultStore(db_path=tmp_path / "v.db", password="anything")
        assert store.verify_password() is True

    def test_correct_password_verifies(self, tmp_path):
        store = VaultStore(db_path=tmp_path / "v.db", password="correct")
        store.add_key("p", "kimi", "https://a.com", "sk-1")
        assert store.verify_password() is True

    def test_wrong_password_rejected(self, tmp_path):
        db = tmp_path / "v.db"
        VaultStore(db_path=db, password="correct").add_key("p", "kimi", "https://a.com", "sk-1")
        wrong = VaultStore(db_path=db, password="wrong")
        assert wrong.verify_password() is False
