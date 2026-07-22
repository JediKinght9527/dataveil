"""Sync base interface (Pro feature)."""
from abc import ABC, abstractmethod
from pathlib import Path


class SyncBackend(ABC):
    @abstractmethod
    def upload(self, local_path: Path, remote_key: str) -> bool:
        ...

    @abstractmethod
    def download(self, remote_key: str, local_path: Path) -> bool:
        ...
