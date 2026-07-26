"""In-memory sync backend for testing and local development."""

from pathlib import Path
from typing import Optional

from dv.sync.base import SyncBackend


class MemoryBackend(SyncBackend):
    """Store objects in memory (useful for testing)."""

    def __init__(self):
        self._store: dict[str, bytes] = {}

    def upload(self, local_path: Path, remote_key: str) -> bool:
        try:
            self._store[remote_key] = local_path.read_bytes()
            return True
        except OSError:
            return False

    def download(self, remote_key: str, local_path: Path) -> bool:
        data = self._store.get(remote_key)
        if data is None:
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        return True

    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        self._store[remote_key] = data
        return True

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        return self._store.get(remote_key)

    def exists(self, remote_key: str) -> bool:
        return remote_key in self._store

    def list_objects(self, prefix: str = "") -> list[str]:
        return [k for k in self._store if k.startswith(prefix)]
