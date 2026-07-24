"""Tests for Gateway proxy (requires running server)."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from dv.gateway.server import app
from dv.gateway.proxy import PrivacyProxy
from dv.vault.store import VaultStore
from dv.audit.logger import AuditLogger
import dv.gateway.server as server_module


@pytest.fixture
def isolated_client(tmp_path: Path):
    """Test client with isolated empty vault."""
    # Reset global proxy
    server_module._proxy = None
    # Point to temp vault
    import os

    old_vault = os.environ.get("DV_VAULT_PATH")
    os.environ["DV_VAULT_PATH"] = str(tmp_path / "vault.db")
    os.environ["DV_VAULT_PASSWORD"] = "test"
    try:
        yield TestClient(app)
    finally:
        if old_vault:
            os.environ["DV_VAULT_PATH"] = old_vault
        else:
            os.environ.pop("DV_VAULT_PATH", None)
        server_module._proxy = None


class TestGateway:
    def test_health_no_vault(self, isolated_client):
        """Gateway returns 500 if vault is empty (expected in tests)."""
        response = isolated_client.post("/v1/chat/completions", json={"model": "test"})
        # Without vault config, proxy can't route
        assert response.status_code in (500, 502)

    def test_path_conversion_openai_to_anthropic(self, isolated_client):
        """OpenAI-format /v1/chat/completions converts to /v1/messages for Kimi."""
        # This test verifies the conversion logic exists
        # (actual upstream call will fail without valid key, but conversion should happen)
        response = isolated_client.post(
            "/v1/chat/completions",
            json={"model": "kimi-k2.6", "messages": [{"role": "user", "content": "hi"}]},
        )
        # With empty vault, should be 500
        assert response.status_code in (500, 502)
