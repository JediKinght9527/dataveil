"""Tests for sync engine."""

from pathlib import Path

import pytest

from dv.sync.engine import SyncEngine
from dv.sync.memory import MemoryBackend


class TestSyncEngine:
    @pytest.fixture
    def engine(self, tmp_path: Path):
        backend = MemoryBackend()
        state_path = tmp_path / "sync_state.json"
        return SyncEngine(
            backend=backend,
            encrypt_key="test-encryption-key",
            state_path=state_path,
        )

    def test_sync_file(self, engine, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        assert engine.sync_file(test_file) is True
        assert engine.backend.exists("test.txt")

    def test_sync_file_unchanged(self, engine, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        assert engine.sync_file(test_file) is True
        # Second sync should skip (unchanged)
        assert engine.sync_file(test_file) is False

    def test_sync_file_changed(self, engine, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        assert engine.sync_file(test_file) is True
        test_file.write_text("hello world")
        assert engine.sync_file(test_file) is True

    def test_download_file(self, engine, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("secret data")
        engine.sync_file(test_file)

        download_path = tmp_path / "downloaded.txt"
        assert engine.download_file("test.txt", download_path) is True
        assert download_path.read_text() == "secret data"

    def test_sync_vault(self, engine, tmp_path):
        vault_file = tmp_path / "vault.db"
        vault_file.write_text("encrypted vault data")
        assert engine.sync_vault(vault_file) is True
        assert engine.backend.exists("vault.db.enc")

    def test_sync_audit_log(self, engine, tmp_path):
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        (audit_dir / "audit.2024-01-01.jsonl").write_text("log1")
        (audit_dir / "audit.2024-01-02.jsonl").write_text("log2")
        synced = engine.sync_audit_log(audit_dir)
        assert synced == 2
        assert engine.backend.exists("audit/audit.2024-01-01.jsonl.enc")

    def test_sync_status(self, engine, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("data")
        engine.sync_file(test_file)
        status = engine.get_sync_status()
        assert status["tracked_files"] == 1
        assert status["backend"] == "MemoryBackend"
        assert status["last_sync"] > 0
