"""Audit logging with rotation, scrubbing, and query support."""

import json
import re
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional


class AuditLogger:
    """Append-only JSON Lines audit log with rotation."""

    def __init__(
        self,
        log_path: Path,
        enabled: bool = True,
        retention_days: int = 30,
        scrub_sensitive: bool = True,
    ):
        self.log_path = log_path
        self.enabled = enabled
        self.retention_days = retention_days
        self.scrub_sensitive = scrub_sensitive
        if enabled:
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def _current_log_file(self) -> Path:
        """Get today's log file with rotation."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_path.parent / f"{self.log_path.stem}.{today}{self.log_path.suffix}"

    def _rotate_if_needed(self) -> None:
        """Rotate old logs and cleanup expired files."""
        current = self._current_log_file()
        if current.exists():
            return

        # Create new file
        current.touch()

        # Cleanup old logs
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        for f in self.log_path.parent.glob(f"{self.log_path.stem}.*{self.log_path.suffix}"):
            try:
                date_str = f.stem.split(".")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    f.unlink()
            except (ValueError, IndexError):
                continue

    def _scrub(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove or hash sensitive fields from log entry."""
        if not self.scrub_sensitive:
            return data

        scrubbed = data.copy()
        # Scrub API key patterns in any string field
        for key, value in scrubbed.items():
            if isinstance(value, str):
                scrubbed[key] = re.sub(
                    r"sk-\w{24,}",
                    lambda m: f"sk-***{hash(m.group()) % 10000:04d}",
                    value,
                )
        return scrubbed

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
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        self._rotate_if_needed()

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
        if extra:
            entry.update(extra)

        entry = self._scrub(entry)

        log_file = self._current_log_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def query(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status_code: Optional[int] = None,
        profile: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit logs with filters."""
        results: list[dict[str, Any]] = []

        for entry in self._iter_entries():
            if start_time and entry.get("timestamp", "") < start_time.isoformat():
                continue
            if end_time and entry.get("timestamp", "") > end_time.isoformat():
                continue
            if status_code and entry.get("status_code") != status_code:
                continue
            if profile and entry.get("profile") != profile:
                continue
            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def _iter_entries(self) -> Iterator[dict[str, Any]]:
        """Iterate over all log entries, newest first."""
        log_files = sorted(
            self.log_path.parent.glob(f"{self.log_path.stem}.*{self.log_path.suffix}"),
            reverse=True,
        )
        for log_file in log_files:
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            yield json.loads(line)
            except (OSError, json.JSONDecodeError):
                continue
