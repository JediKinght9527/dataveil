"""Base sync backend interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class SyncBackend(ABC):
    """Abstract interface for object storage backends."""

    @abstractmethod
    def upload(self, local_path: Path, remote_key: str) -> bool:
        """Upload a file to remote storage."""
        ...

    @abstractmethod
    def download(self, remote_key: str, local_path: Path) -> bool:
        """Download a file from remote storage."""
        ...

    @abstractmethod
    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        """Upload raw bytes to remote storage."""
        ...

    @abstractmethod
    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        """Download raw bytes from remote storage."""
        ...

    @abstractmethod
    def exists(self, remote_key: str) -> bool:
        """Check if a remote object exists."""
        ...

    @abstractmethod
    def list_objects(self, prefix: str = "") -> list[str]:
        """List objects with optional prefix filter."""
        ...
