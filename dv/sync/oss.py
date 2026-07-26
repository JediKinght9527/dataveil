"""Aliyun OSS sync backend."""

from pathlib import Path
from typing import Optional

from dv.sync.base import SyncBackend


class OSSBackend(SyncBackend):
    """Aliyun OSS backend using oss2 SDK."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint: str,
        bucket: str,
        prefix: str = "dataveil/",
    ):
        try:
            import oss2  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("oss2 is required for Aliyun OSS backend. pip install oss2") from e

        self.auth = oss2.Auth(access_key, secret_key)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket)
        self.prefix = prefix

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}{remote_key}"

    def upload(self, local_path: Path, remote_key: str) -> bool:
        try:
            self.bucket.put_object_from_file(self._key(remote_key), str(local_path))
            return True
        except Exception:
            return False

    def download(self, remote_key: str, local_path: Path) -> bool:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.bucket.get_object_to_file(self._key(remote_key), str(local_path))
            return True
        except Exception:
            return False

    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        try:
            self.bucket.put_object(self._key(remote_key), data)
            return True
        except Exception:
            return False

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        try:
            result = self.bucket.get_object(self._key(remote_key))
            return result.read()
        except Exception:
            return None

    def exists(self, remote_key: str) -> bool:
        try:
            return self.bucket.object_exists(self._key(remote_key))
        except Exception:
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        try:
            result = self.bucket.list_objects(f"{self.prefix}{prefix}")
            return [obj.key for obj in result.object_list]
        except Exception:
            return []
