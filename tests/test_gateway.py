"""Tests for Gateway proxy (requires running server)."""
import pytest
from fastapi.testclient import TestClient

from dv.gateway.server import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGateway:
    def test_health_no_vault(self, client):
        """Gateway returns 500 if vault is empty (expected in tests)."""
        response = client.post("/v1/chat/completions", json={"model": "test"})
        # Without vault config, proxy can't route
        assert response.status_code in (500, 502)
