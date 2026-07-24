"""FastAPI server with catch-all route, health check, and metrics."""
from __future__ import annotations

from fastapi import FastAPI, Request

from dv.audit.logger import AuditLogger
from dv.config import load_config
from dv.gateway.proxy import PrivacyProxy
from dv.vault.store import VaultStore

app = FastAPI(title="DataVeil Gateway", version="0.1.0")

# Lazy init on first request to avoid startup crypto overhead
_proxy: PrivacyProxy | None = None


def get_proxy() -> PrivacyProxy:
    global _proxy
    if _proxy is None:
        config = load_config()
        password = config.vault.keyring_account or "changeme"
        vault = VaultStore(db_path=config.vault.path, password=password)
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
    proxy = get_proxy()
    vault_ok = proxy.vault is not None
    return {
        "status": "healthy" if vault_ok else "degraded",
        "vault": "ok" if vault_ok else "error",
        "version": "0.1.0",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    proxy = get_proxy()
    return proxy._metrics.snapshot()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def catch_all(request: Request, path: str):
    proxy = get_proxy()
    return await proxy.handle(request, path)
