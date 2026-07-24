"""Gateway proxy with inline privacy processing and performance optimizations."""
from __future__ import annotations

import json
import time
from typing import Any

import httpx
from fastapi import Request, Response

from dv.audit.logger import AuditLogger
from dv.privacy.engine import PrivacyEngine
from dv.vault.store import VaultStore


class PerformanceMetrics:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0.0
        self.entities_detected_total = 0
        self.last_request_time: float | None = None

    def record(self, duration_ms: float, entities: int, error: bool = False):
        self.request_count += 1
        self.total_duration_ms += duration_ms
        self.entities_detected_total += entities
        self.last_request_time = time.time()
        if error:
            self.error_count += 1

    @property
    def avg_duration_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_duration_ms / self.request_count

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests_total": self.request_count,
            "errors_total": self.error_count,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "entities_detected_total": self.entities_detected_total,
            "last_request_time": self.last_request_time,
        }


class PrivacyProxy:
    """Proxy requests to LLM providers with privacy processing."""

    # Class-level compiled regex patterns (compile once, reuse)
    _metrics = PerformanceMetrics()

    def __init__(
        self,
        vault: VaultStore,
        audit: AuditLogger,
        profile: str = "default",
        cache_ttl_seconds: int = 300,
    ):
        self.vault = vault
        self.audit = audit
        self.profile = profile
        self.engine = PrivacyEngine()
        self._cache_ttl = cache_ttl_seconds

        # Vault config cache: profile -> (config, timestamp)
        self._config_cache: dict[str, tuple[dict[str, Any], float]] = {}

        # Reusable HTTP client (connection pooling)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create reusable HTTP client with connection pooling."""
        client = getattr(self, "_client", None)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0,
                ),
            )
            self._client = client
        return client

    def _get_cached_config(self, profile: str) -> dict[str, Any] | None:
        """Get vault config with TTL cache to avoid repeated Argon2id decryption."""
        now = time.time()
        ttl = getattr(self, "_cache_ttl", 300)
        cache = getattr(self, "_config_cache", None)
        if cache is None:
            cache = {}
            self._config_cache = cache

        if profile in cache:
            config, cached_at = cache[profile]
            if now - cached_at < ttl:
                return config

        config = self.vault.get_key(profile)
        if config:
            cache[profile] = (config, now)
        return config

    def _resolve_profile(self, path: str) -> str:
        """Resolve profile, with fallback for OpenAI-format paths."""
        if self._get_cached_config(self.profile):
            return self.profile
        if self._get_cached_config("work"):
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
            data = json.loads(body.decode("utf-8"))
            if "messages" in data and isinstance(data["messages"], list):
                if "max_tokens" not in data:
                    data["max_tokens"] = 4096
                for msg in data["messages"]:
                    if msg.get("role") == "system":
                        data["system"] = msg["content"]
                        data["messages"] = [m for m in data["messages"] if m.get("role") != "system"]
                        break
            return json.dumps(data, ensure_ascii=False).encode("utf-8")
        except Exception:
            return body

    def _redact_json_body(self, body: bytes) -> tuple[bytes, dict[str, str]]:
        """Redact decoded JSON values, then serialize safely."""
        payload = json.loads(body.decode("utf-8"))
        counters: dict[str, int] = {}
        mapping: dict[str, str] = {}

        def redact_string(value: str) -> str:
            entities = self.engine.detector.detect(value)
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
        request_id = str(id(request))

        # 1. Resolve profile with cache
        profile = self._resolve_profile(path)
        config = self._get_cached_config(profile)
        if not config:
            duration = (time.perf_counter() - start) * 1000
            self._metrics.record(duration, 0, error=True)
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

        # 2. Convert path and body
        converted_path = self._convert_path(path, config["provider"])
        body = await request.body()
        body = self._convert_body(body, converted_path, config["provider"])

        # 3. Privacy detection & replacement
        try:
            replaced, mapping = self._redact_json_body(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            duration = (time.perf_counter() - start) * 1000
            self._metrics.record(duration, 0, error=True)
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
        for h in ("x-request-id", "accept", "accept-encoding"):
            if h in request.headers:
                headers[h] = request.headers[h]

        # 4. Forward with connection pooling and retry
        client = await self._get_client()
        upstream_content = b""
        content_type = "application/json"
        upstream_status = 502
        upstream_error = None

        for attempt in range(2):
            try:
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
            self._metrics.record(duration, entities_count, error=True)
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

        # 5. Rehydrate response
        is_sse = "text/event-stream" in content_type

        if is_sse:
            text_sse = upstream_content.decode("utf-8", errors="replace")
            final_sse = "".join(
                self.engine.restore_stream(iter(text_sse.splitlines(keepends=True)), mapping)
            )
            duration = (time.perf_counter() - start) * 1000
            self._metrics.record(duration, entities_count)
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
                content=final_sse,
                status_code=upstream_status,
                media_type="text/event-stream",
            )

        # Non-streaming
        try:
            response_payload = json.loads(upstream_content.decode("utf-8"))
            final = json.dumps(
                self.engine.restore_json(response_payload, mapping),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            final = upstream_content

        duration = (time.perf_counter() - start) * 1000
        self._metrics.record(duration, entities_count)
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

    async def close(self) -> None:
        """Cleanup resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
