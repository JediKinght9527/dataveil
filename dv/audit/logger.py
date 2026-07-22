"""Audit logging with structured JSON Lines output."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AuditLogger:
    """Append-only JSON Lines audit log."""

    def __init__(self, log_path: Path, enabled: bool = True):
        self.log_path = log_path
        self.enabled = enabled
        if enabled:
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        profile: str,
        provider: str,
        status_code: int,
        duration_ms: float,
        entities_detected: int = 0,
        error: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "profile": profile,
            "provider": provider,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "entities_detected": entities_detected,
        }
        if error:
            entry["error"] = error

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
