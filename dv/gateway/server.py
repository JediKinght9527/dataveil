"""FastAPI server with catch-all route."""
from __future__ import annotations

from fastapi import FastAPI, Request

from dv.config import get_settings
from dv.gateway.proxy import PrivacyProxy
from dv.vault.store import VaultStore
from dv.audit.logger import AuditLogger

app = FastAPI(title="DataVeil Gateway", version="0.1.0")

# Lazy init on first request to avoid startup crypto overhead
_proxy: PrivacyProxy | None = None


def get_proxy() -> PrivacyProxy:
    global _proxy
    if _proxy is None:
        settings = get_settings()
        # TODO: interactive password unlock or keychain
        password = settings.vault_password or "changeme"
        vault = VaultStore(db_path=settings.vault_path, password=password)
        audit = AuditLogger(log_path=settings.audit_log_path, enabled=settings.audit_enabled)
        _proxy = PrivacyProxy(vault=vault, audit=audit, profile=settings.default_profile)
    return _proxy


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def catch_all(request: Request, path: str):
    proxy = get_proxy()
    return await proxy.handle(request, path)
