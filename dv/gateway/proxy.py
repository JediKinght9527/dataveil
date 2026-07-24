"""Gateway proxy with inline privacy processing."""
import json
import time
from typing import Any

import httpx
from fastapi import Request, Response

from dv.audit.logger import AuditLogger
from dv.privacy.engine import PrivacyEngine
from dv.vault.store import VaultStore


class PrivacyProxy:
    """Proxy requests to LLM providers with privacy processing."""

    def __init__(
        self,
        vault: VaultStore,
        audit: AuditLogger,
        profile: str = "default",
    ):
        self.vault = vault
        self.audit = audit
        self.profile = profile
        self.engine = PrivacyEngine()

    def _resolve_profile(self, path: str) -> str:
        """Resolve profile, with fallback for OpenAI-format paths."""
        # If the requested profile exists, use it
        if self.vault.get_key(self.profile):
            return self.profile
        # Fallback: try 'work' profile for any path
        if self.vault.get_key("work"):
            return "work"
        return self.profile

    def _convert_path(self, path: str, provider: str) -> str:
        """Convert OpenAI-format paths to Anthropic-format if needed."""
        if provider in ("kimi", "anthropic"):
            if path == "v1/chat/completions":
                return "v1/messages"
            if path == "v1/completions":
                return "v1/complete"
        return path

    def _convert_body(self, body: bytes, path: str, provider: str) -> bytes:
        """Convert OpenAI chat format to Anthropic messages format."""
        if provider not in ("kimi", "anthropic"):
            return body
        if path not in ("v1/chat/completions", "v1/messages"):
            return body

        try:
            import json

            data = json.loads(body.decode("utf-8"))
            # Convert OpenAI format to Anthropic format
            if "messages" in data and isinstance(data["messages"], list):
                # Ensure max_tokens exists for Anthropic
                if "max_tokens" not in data:
                    data["max_tokens"] = 4096
                # Convert system message if present
                for msg in data["messages"]:
                    if msg.get("role") == "system":
                        data["system"] = msg["content"]
                        data["messages"] = [m for m in data["messages"] if m.get("role") != "system"]
                        break
            return json.dumps(data, ensure_ascii=False).encode("utf-8")
        except Exception:
            return body

    def _redact_json_body(self, body: bytes) -> tuple[bytes, dict[str, str]]:
        """Redact decoded JSON values, then serialize safely.

        Do not run string substitution over JSON source. It can invalidate a
        JSON escape sequence when the sensitive span begins after a backslash.
        """
        payload = json.loads(body.decode("utf-8"))
        counters: dict[str, int] = {}
        mapping: dict[str, str] = {}

        def redact_string(value: str) -> str:
            entities = self.engine.detector.detect(value)
            # Rules may overlap. Keep the first span in detector order and
            # replace right-to-left so offsets remain valid.
            selected = []
            occupied_until = -1
            for entity in entities:
                if entity.start >= occupied_until:
                    selected.append(entity)
                    occupied_until = entity.end
            redacted = value
            for entity in reversed(selected):
                counters[entity.entity_type] = counters.get(entity.entity_type, 0) + 1
                token = f"<{entity.entity_type.upper()}_{counters[entity.entity_type]}>"
                mapping[token] = entity.text
                redacted = redacted[:entity.start] + token + redacted[entity.end:]
            return redacted

        def walk(value: Any) -> Any:
            if isinstance(value, str):
                return redact_string(value)
            if isinstance(value, list):
                return [walk(item) for item in value]
            if isinstance(value, dict):
                return {key: walk(item) for key, item in value.items()}
            return value

        redacted = json.dumps(walk(payload), ensure_ascii=False, separators=(",", ":"))
        return redacted.encode("utf-8"), mapping

    async def handle(self, request: Request, path: str) -> Response:
        start = time.perf_counter()
        request_id = str(id(request))  # Simple unique ID

        # 1. Resolve profile with fallback
        profile = self._resolve_profile(path)
        config = self.vault.get_key(profile)
        if not config:
            duration = (time.perf_counter() - start) * 1000
            self.audit.log(
                request_id=request_id,
                method=request.method,
                path=path,
                profile=profile,
                provider="unknown",
                status_code=500,
                duration_ms=duration,
                error="Vault profile not found",
            )
            return Response(
                content='{"error":"Vault profile not found"}',
                status_code=500,
                media_type="application/json",
            )

        # 2. Convert path and body for Anthropic-compatible upstreams
        converted_path = self._convert_path(path, config["provider"])

        # 3. Read body
        body = await request.body()

        # 4. Convert OpenAI format to Anthropic format if needed
        body = self._convert_body(body, converted_path, config["provider"])

        # 5. Privacy detection & replacement. The upstream APIs use JSON;
        # parse it first so redaction cannot corrupt escape sequences.
        try:
            replaced, mapping = self._redact_json_body(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(
                content='{"error":"Request body must be valid UTF-8 JSON"}',
                status_code=400,
                media_type="application/json",
            )
        entities_count = len(mapping)

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        # Forward selected headers
        for h in ("x-request-id", "accept", "accept-encoding"):
            if h in request.headers:
                headers[h] = request.headers[h]

        # Fully read the upstream response inside the client context. The old
        # code returned a streaming response after this context closed, which
        # made intermittent upstream socket resets surface as local HTTP 500s.
        upstream_content = b""
        content_type = "application/json"
        upstream_status = 502
        upstream_error = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                    upstream_req = client.build_request(
                        method=request.method,
                        url=f"{config['base_url'].rstrip('/')}/{converted_path}",
                        headers=headers,
                        content=replaced,
                    )
                    upstream_resp = await client.send(upstream_req, stream=True)
                    upstream_content = await upstream_resp.aread()
                    content_type = upstream_resp.headers.get("content-type", "application/json")
                    upstream_status = upstream_resp.status_code
                    upstream_error = None
                    break
            except httpx.HTTPError as exc:
                upstream_error = exc
                if attempt == 0:
                    continue
            except Exception as exc:
                upstream_error = exc
                break
        if upstream_error is not None:
            duration = (time.perf_counter() - start) * 1000
            self.audit.log(
                request_id=request_id,
                method=request.method,
                path=converted_path,
                profile=profile,
                provider=config["provider"],
                status_code=502,
                duration_ms=duration,
                error=str(upstream_error),
            )
            return Response(
                content='{"error":"Upstream connection failed; retry the request"}',
                status_code=502,
                media_type="application/json",
            )

        # 4. Rehydrate after the upstream socket is safely closed.
        is_sse = "text/event-stream" in content_type

        if is_sse:
            text_sse = upstream_content.decode("utf-8", errors="replace")
            final_sse = "".join(self.engine.restore_stream(iter(text_sse.splitlines(keepends=True)), mapping))
            duration = (time.perf_counter() - start) * 1000
            self.audit.log(
                request_id=request_id,
                method=request.method,
                path=converted_path,
                profile=profile,
                provider=config["provider"],
                status_code=upstream_status,
                duration_ms=duration,
                entities_detected=entities_count,
            )
            return Response(content=final_sse, status_code=upstream_status, media_type="text/event-stream")

        # Non-streaming
        try:
            response_payload = json.loads(upstream_content.decode("utf-8"))
            final = json.dumps(
                self.engine.restore_json(response_payload, mapping),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Do not attempt raw string substitution in a non-JSON body;
            # returning it unchanged is safer than emitting malformed JSON.
            final = upstream_content
        duration = (time.perf_counter() - start) * 1000
        self.audit.log(
            request_id=request_id,
            method=request.method,
            path=converted_path,
            profile=profile,
            provider=config["provider"],
            status_code=upstream_status,
            duration_ms=duration,
            entities_detected=entities_count,
        )
        return Response(
            content=final,
            status_code=upstream_status,
            media_type="application/json",
        )
