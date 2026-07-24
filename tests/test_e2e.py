"""End-to-end integration tests with mock LLM upstream."""
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient

from dv.audit.logger import AuditLogger
from dv.gateway.proxy import PrivacyProxy
from dv.vault.store import VaultStore


# Mock LLM upstream server
mock_upstream = FastAPI()


@mock_upstream.post("/v1/messages")
async def mock_messages(request: dict):
    """Mock Anthropic messages endpoint."""
    content = request["messages"][0]["content"]
    return JSONResponse({
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": f"Echo: {content}"}],
        "model": request.get("model", "test"),
        "stop_reason": "end_turn",
    })


@mock_upstream.post("/v1/chat/completions")
async def mock_chat_completions(request: dict):
    """Mock OpenAI chat completions endpoint."""
    content = request["messages"][0]["content"]
    return JSONResponse({
        "id": "chatcmpl_test",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": f"Echo: {content}"},
            "finish_reason": "stop",
        }],
    })


@mock_upstream.post("/v1/messages/stream")
async def mock_messages_stream():
    """Mock SSE streaming endpoint."""
    async def event_stream():
        chunks = [
            {"type": "content_block_delta", "delta": {"text": "Hello"}},
            {"type": "content_block_delta", "delta": {"text": " world"}},
            {"type": "message_stop"},
        ]
        for chunk in chunks:
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class TestE2E:
    @pytest.fixture
    def proxy(self, tmp_path):
        vault = VaultStore(db_path=tmp_path / "vault.db", password="test")
        vault.add_key("test", "kimi", "http://mock-upstream", "sk-test-key")
        audit = AuditLogger(log_path=tmp_path / "audit.jsonl", enabled=False)
        return PrivacyProxy(vault=vault, audit=audit, profile="test")

    @pytest.mark.asyncio
    async def test_full_chain_redaction_and_rehydration(self, proxy, monkeypatch):
        """Test complete flow: request → redact → forward → rehydrate → response."""
        # Mock the upstream call
        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def build_request(self, **kwargs):
                return kwargs

            async def send(self, request, stream=True):
                # Verify the request was redacted
                body = request["content"].decode()
                assert "marco@example.com" not in body
                assert "<EMAIL_1>" in body

                # Return response with placeholder
                return httpx.Response(
                    200,
                    json={"content": [{"text": "Contact <EMAIL_1> for help"}]},
                )

        async def mock_get_client():
            return MockClient()

        monkeypatch.setattr(proxy, "_get_client", mock_get_client)

        # Simulate request
        from starlette.requests import Request

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "kimi-k2.6",
                    "messages": [{"role": "user", "content": "Email me at marco@example.com"}],
                }).encode(),
                "more_body": False,
            }

        request = Request(
            {"type": "http", "method": "POST", "headers": [(b"content-type", b"application/json")]},
            receive=receive,
        )

        response = await proxy.handle(request, "v1/messages")
        assert response.status_code == 200

        # Verify response was rehydrated
        body = json.loads(response.body)
        assert "marco@example.com" in str(body)

    @pytest.mark.asyncio
    async def test_openai_to_anthropic_conversion(self, proxy, monkeypatch):
        """Test OpenAI format is converted to Anthropic format."""
        captured_path = None
        captured_body = None

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def build_request(self, **kwargs):
                nonlocal captured_path, captured_body
                captured_path = kwargs["url"]
                captured_body = kwargs["content"].decode()
                return kwargs

            async def send(self, request, stream=True):
                return httpx.Response(200, json={"content": []})

        async def mock_get_client():
            return MockClient()

        monkeypatch.setattr(proxy, "_get_client", mock_get_client)

        from starlette.requests import Request

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "kimi-k2.6",
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 100,
                }).encode(),
                "more_body": False,
            }

        request = Request(
            {"type": "http", "method": "POST", "headers": [(b"content-type", b"application/json")]},
            receive=receive,
        )

        response = await proxy.handle(request, "v1/chat/completions")
        assert response.status_code == 200
        assert "/v1/messages" in captured_path

    @pytest.mark.asyncio
    async def test_concurrent_requests_consistent_mapping(self, proxy, monkeypatch):
        """Test that concurrent requests maintain consistent placeholder mapping."""
        import asyncio

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def build_request(self, **kwargs):
                return kwargs

            async def send(self, request, stream=True):
                body = request["content"].decode()
                # Return the redacted body back
                return httpx.Response(200, json={"echo": body})

        async def mock_get_client():
            return MockClient()

        monkeypatch.setattr(proxy, "_get_client", mock_get_client)

        from starlette.requests import Request

        async def make_request(content: str):
            async def receive():
                return {
                    "type": "http.request",
                    "body": json.dumps({
                        "model": "test",
                        "messages": [{"role": "user", "content": content}],
                    }).encode(),
                    "more_body": False,
                }

            return Request(
                {"type": "http", "method": "POST", "headers": [(b"content-type", b"application/json")]},
                receive=receive,
            )

        # Run concurrent requests
        request_contents = [
            "email alice@test.com",
            "email bob@test.com",
            "email alice@test.com",  # Same as first
        ]

        requests = [await make_request(c) for c in request_contents]

        responses = await asyncio.gather(*[
            proxy.handle(req, "v1/messages") for req in requests
        ])

        assert all(r.status_code == 200 for r in responses)

        # First and third should have same placeholder for same email
        body1 = json.loads(responses[0].body)
        body3 = json.loads(responses[2].body)
        assert body1 == body3
