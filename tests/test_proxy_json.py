"""Regression tests for JSON-safe gateway transformations."""
import json

import httpx
import pytest

from dv.gateway.proxy import PrivacyProxy


def test_redaction_keeps_json_valid_near_escaped_content():
    proxy = object.__new__(PrivacyProxy)
    proxy.engine = __import__("dv.privacy.engine", fromlist=["PrivacyEngine"]).PrivacyEngine()
    body = json.dumps(
        {"messages": [{"content": r"literal \\ and marco@example.com"}]}
    ).encode()

    redacted, mapping = proxy._redact_json_body(body)

    payload = json.loads(redacted)
    assert "marco@example.com" not in payload["messages"][0]["content"]
    assert "<EMAIL_1>" in payload["messages"][0]["content"]
    assert mapping["<EMAIL_1>"] == "marco@example.com"


@pytest.mark.asyncio
async def test_proxy_retries_transient_upstream_read_error(monkeypatch):
    """A transient upstream socket reset must not become an unhandled 500."""
    from dv.gateway import proxy as proxy_module

    class Client:
        calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def build_request(self, **kwargs):
            return kwargs

        async def send(self, _request, stream=True):
            Client.calls += 1
            if Client.calls == 1:
                raise httpx.ReadError("dropped")
            return httpx.Response(200, json={"type": "message", "content": []})

    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", lambda **_kwargs: Client())
    proxy = object.__new__(PrivacyProxy)
    proxy.engine = __import__("dv.privacy.engine", fromlist=["PrivacyEngine"]).PrivacyEngine()
    proxy.vault = type("Vault", (), {"get_key": lambda *_: {"api_key": "test", "base_url": "https://example.test", "provider": "test"}})()
    proxy.audit = type("Audit", (), {"log": lambda *_args, **_kwargs: None})()
    proxy.profile = "test"

    from starlette.requests import Request

    async def receive():
        return {"type": "http.request", "body": json.dumps({"messages": [{"content": "hello"}]}).encode(), "more_body": False}

    request = Request({"type": "http", "method": "POST", "headers": [(b"content-type", b"application/json")], "path": "/v1/messages"}, receive=receive)
    response = await proxy.handle(request, "v1/messages")
    assert response.status_code == 200
    assert Client.calls == 2
