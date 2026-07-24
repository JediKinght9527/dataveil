"""OSS sync engine with client-side encryption."""
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from dv.vault.crypto import VaultCrypto


@dataclass
class SyncState:
    """Track sync state for incremental uploads."""
    last_sync: float = 0.0
    file_hashes: Dict[str, str] = None  # path -> sha256

    def __post_init__(self):
        if self.file_hashes is None:
            self.file_hashes = {}


class SyncEngine:
    """Synchronize encrypted files to object storage."""

    def __init__(
        self,
        backend,
        encrypt_key: str,
        state_path: Optional[Path] = None,
    ):
        self.backend = backend
        self.encrypt_key = encrypt_key
        self.state_path = state_path or Path.home() / ".dataveil" / "sync_state.json"
        self.state = self._load_state()

    def _load_state(self) -> SyncState:
        if not self.state_path.exists():
            return SyncState()
        try:
            with open(self.state_path, encoding="utf-8") as f:
                data = json.load(f)
            return SyncState(**data)
        except Exception:
            return SyncState()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.state), f, indent=2)

    @staticmethod
    def _hash_file(path: Path) -> str:
        """Compute SHA256 of file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _should_sync(self, path: Path) -> bool:
        """Check if file needs sync (changed since last sync)."""
        if not path.exists():
            return False
        current_hash = self._hash_file(path)
        cached_hash = self.state.file_hashes.get(str(path))
        return current_hash != cached_hash

    def sync_file(self, local_path: Path, remote_key: Optional[str] = None) -> bool:
        """Sync a single file to remote storage."""
        if not self._should_sync(local_path):
            return False

        remote_key = remote_key or local_path.name

        # Read and encrypt
        plaintext = local_path.read_bytes()
        encrypted = VaultCrypto.encrypt(plaintext, self.encrypt_key)

        # Upload via backend
        success = self.backend.upload_bytes(encrypted, remote_key)

        if success:
            self.state.file_hashes[str(local_path)] = self._hash_file(local_path)
            self.state.last_sync = time.time()
            self._save_state()

        return success

    def sync_vault(self, vault_path: Path) -> bool:
        """Sync vault database."""
        return self.sync_file(vault_path, remote_key="vault.db.enc")

    def sync_audit_log(self, audit_dir: Path) -> int:
        """Sync all audit log files."""
        synced = 0
        for log_file in audit_dir.glob("audit.*.jsonl"):
            if self.sync_file(log_file, remote_key=f"audit/{log_file.name}.enc"):
                synced += 1
        return synced

    def download_file(self, remote_key: str, local_path: Path) -> bool:
        """Download and decrypt a file from remote storage."""
        encrypted = self.backend.download_bytes(remote_key)
        if encrypted is None:
            return False

        plaintext = VaultCrypto.decrypt(encrypted, self.encrypt_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(plaintext)

        # Update state
        self.state.file_hashes[str(local_path)] = self._hash_file(local_path)
        self._save_state()
        return True

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "last_sync": self.state.last_sync,
            "last_sync_human": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.state.last_sync)
            ) if self.state.last_sync else "never",
            "tracked_files": len(self.state.file_hashes),
            "backend": self.backend.__class__.__name__,
        }
