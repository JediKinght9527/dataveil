"""Gateway proxy with inline privacy processing."""
import time
from typing import Any, Dict

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

    async def handle(self, request: Request, path: str) -> Response:
        start = time.perf_counter()
        request_id = str(id(request))  # Simple unique ID

        # 1. Read body
        body = await request.body()
        text = body.decode("utf-8", errors="ignore")

        # 2. Privacy detection & replacement
        replaced, mapping = self.engine.process(text)
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
                    content=replaced.encode("utf-8"),
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
            rehydrator = self.engine.restore_stream([], mapping)

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
        text_resp = content.decode("utf-8", errors="ignore")
        final = self.engine.restore(text_resp, mapping)
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
