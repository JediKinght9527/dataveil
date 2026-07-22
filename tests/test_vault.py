"""Tests for Vault encryption and storage."""
from dv.vault.crypto import VaultCrypto
from dv.vault.store import VaultStore


class TestVaultCrypto:
    def test_roundtrip(self):
        password = "my-secret-password"
        plaintext = b"sk-test-api-key-12345"
        token = VaultCrypto.encrypt(plaintext, password)
        decrypted = VaultCrypto.decrypt(token, password)
        assert decrypted == plaintext

    def test_wrong_password_fails(self):
        token = VaultCrypto.encrypt(b"secret", "correct")
        with pytest.raises(Exception):
            VaultCrypto.decrypt(token, "wrong")


class TestVaultStore:
    def test_add_and_get(self, temp_vault):
        temp_vault.add_key("work", "kimi", "https://api.moonshot.cn/anthropic", "sk-abc123")
        config = temp_vault.get_key("work")
        assert config is not None
        assert config["provider"] == "kimi"
        assert config["api_key"] == "sk-abc123"

    def test_get_missing(self, temp_vault):
        assert temp_vault.get_key("nonexistent") is None

    def test_list_profiles(self, temp_vault):
        temp_vault.add_key("work", "kimi", "https://a.com", "sk-1")
        temp_vault.add_key("personal", "openai", "https://b.com", "sk-2")
        profiles = temp_vault.list_profiles()
        assert sorted(profiles) == ["personal", "work"]

    def test_remove(self, temp_vault):
        temp_vault.add_key("tmp", "kimi", "https://a.com", "sk-1")
        assert temp_vault.remove_key("tmp") is True
        assert temp_vault.get_key("tmp") is None
        assert temp_vault.remove_key("tmp") is False


import pytest
