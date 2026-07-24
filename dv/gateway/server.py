"""FastAPI server with catch-all route."""
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
        # TODO: interactive password unlock or keychain
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


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def catch_all(request: Request, path: str):
    proxy = get_proxy()
    return await proxy.handle(request, path)
