"""FastAPI server with catch-all route, health check, and metrics."""

from __future__ import annotations

from fastapi import FastAPI, Request, Response

from dv.audit.logger import AuditLogger
from dv.config import load_config
from dv.gateway.proxy import PrivacyProxy
from dv.vault.store import VaultStore
from dv.vault.unlock import VaultLockedError, require_vault_password

app = FastAPI(title="DataVeil Gateway", version="0.2.0")

# Lazy init on first request to avoid startup crypto overhead
_proxy: PrivacyProxy | None = None


def get_proxy() -> PrivacyProxy:
    global _proxy
    if _proxy is None:
        config = load_config()
        # No default password: resolve from env / keychain, or fail loudly.
        password = require_vault_password(config)
        vault = VaultStore(db_path=config.vault.path, password=password)
        if not vault.verify_password():
            raise VaultLockedError()
        audit = AuditLogger(
            log_path=config.audit.log_path,
            enabled=config.audit.enabled,
            retention_days=config.audit.retention_days,
            scrub_sensitive=config.audit.scrub_sensitive,
        )
        _proxy = PrivacyProxy(vault=vault, audit=audit, profile=config.gateway.default_profile)
    return _proxy


@app.on_event("shutdown")
async def shutdown_event():
    global _proxy
    if _proxy:
        await _proxy.close()


@app.get("/health")
async def health():
    """Health check endpoint for Docker/K8s."""
    try:
        proxy = get_proxy()
    except VaultLockedError:
        return Response(
            content='{"status":"locked","vault":"no password source available"}',
            status_code=503,
            media_type="application/json",
        )
    vault_ok = proxy.vault is not None
    return {
        "status": "healthy" if vault_ok else "degraded",
        "vault": "ok" if vault_ok else "error",
        "version": "0.2.0",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    proxy = get_proxy()
    return proxy._metrics.snapshot()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def catch_all(request: Request, path: str):
    try:
        proxy = get_proxy()
    except VaultLockedError as exc:
        return Response(
            content=f'{{"error":"{exc.args[0].splitlines()[0]}"}}',
            status_code=503,
            media_type="application/json",
        )
    return await proxy.handle(request, path)
