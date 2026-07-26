"""Tests for Audit logger."""

import json
from pathlib import Path

import pytest

from dv.audit.logger import AuditLogger


class TestAuditLogger:
    @pytest.fixture
    def audit(self, tmp_path: Path):
        return AuditLogger(
            log_path=tmp_path / "audit.jsonl",
            enabled=True,
            retention_days=30,
            scrub_sensitive=True,
        )

    def test_log_creates_file(self, audit, tmp_path):
        audit.log(
            request_id="req-1",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=200,
            duration_ms=100.5,
            entities_detected=3,
        )
        log_file = audit._current_log_file()
        assert log_file.exists()
        content = log_file.read_text()
        entry = json.loads(content.strip())
        assert entry["request_id"] == "req-1"
        assert entry["status_code"] == 200
        assert entry["entities_detected"] == 3

    def test_scrubs_api_keys(self, audit):
        audit.log(
            request_id="req-2",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=200,
            duration_ms=50.0,
            error="Invalid key sk-abcdefghijklmnopqrstuvwxyz123456",
        )
        log_file = audit._current_log_file()
        content = log_file.read_text()
        assert "sk-***" in content
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in content

    def test_query_by_status(self, audit):
        audit.log(
            request_id="req-1",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=200,
            duration_ms=100,
        )
        audit.log(
            request_id="req-2",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=500,
            duration_ms=50,
        )
        results = audit.query(status_code=200)
        assert len(results) == 1
        assert results[0]["request_id"] == "req-1"

    def test_query_by_profile(self, audit):
        audit.log(
            request_id="req-1",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=200,
            duration_ms=100,
        )
        audit.log(
            request_id="req-2",
            method="POST",
            path="v1/messages",
            profile="personal",
            provider="openai",
            status_code=200,
            duration_ms=50,
        )
        results = audit.query(profile="work")
        assert len(results) == 1
        assert results[0]["profile"] == "work"

    def test_disabled_logger(self, tmp_path):
        audit = AuditLogger(log_path=tmp_path / "audit.jsonl", enabled=False)
        audit.log(
            request_id="req-1",
            method="POST",
            path="v1/messages",
            profile="work",
            provider="kimi",
            status_code=200,
            duration_ms=100,
        )
        assert not audit._current_log_file().exists()
