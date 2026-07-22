"""Gateway proxy with inline privacy processing."""
import json
import time
from typing import Any

import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

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

        # 1. Read body
        body = await request.body()
        # 2. Privacy detection & replacement. The upstream APIs use JSON;
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

        # 3. Route to upstream
        config = self.vault.get_key(self.profile)
        if not config:
            duration = (time.perf_counter() - start) * 1000
            self.audit.log(
                request_id=request_id,
                method=request.method,
                path=path,
                profile=self.profile,
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

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        # Forward selected headers
        for h in ("x-request-id", "accept", "accept-encoding"):
            if h in request.headers:
                headers[h] = request.headers[h]

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                upstream_req = client.build_request(
                    method=request.method,
                    url=f"{config['base_url'].rstrip('/')}/{path}",
                    headers=headers,
                    content=replaced,
                )
                upstream_resp = await client.send(upstream_req, stream=True)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.audit.log(
                request_id=request_id,
                method=request.method,
                path=path,
                profile=self.profile,
                provider=config["provider"],
                status_code=502,
                duration_ms=duration,
                error=str(e),
            )
            return Response(
                content=f'{{"error":"Upstream error: {e}"}}',
                status_code=502,
                media_type="application/json",
            )

        # 4. Stream or buffer response with rehydration
        content_type = upstream_resp.headers.get("content-type", "")
        is_sse = "text/event-stream" in content_type

        if is_sse:
            async def event_stream():
                async for line in upstream_resp.aiter_text():
                    if line:
                        for out_line in self.engine.restore_stream(
                            iter([line]), mapping
                        ):
                            yield out_line
                duration = (time.perf_counter() - start) * 1000
                self.audit.log(
                    request_id=request_id,
                    method=request.method,
                    path=path,
                    profile=self.profile,
                    provider=config["provider"],
                    status_code=upstream_resp.status_code,
                    duration_ms=duration,
                    entities_detected=entities_count,
                )

            return StreamingResponse(
                event_stream(),
                status_code=upstream_resp.status_code,
                media_type="text/event-stream",
            )

        # Non-streaming
        content = await upstream_resp.aread()
        try:
            response_payload = json.loads(content.decode("utf-8"))
            final = json.dumps(
                self.engine.restore_json(response_payload, mapping),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Do not attempt raw string substitution in a non-JSON body;
            # returning it unchanged is safer than emitting malformed JSON.
            final = content
        duration = (time.perf_counter() - start) * 1000
        self.audit.log(
            request_id=request_id,
            method=request.method,
            path=path,
            profile=self.profile,
            provider=config["provider"],
            status_code=upstream_resp.status_code,
            duration_ms=duration,
            entities_detected=entities_count,
        )
        return Response(
            content=final,
            status_code=upstream_resp.status_code,
            media_type="application/json",
        )
