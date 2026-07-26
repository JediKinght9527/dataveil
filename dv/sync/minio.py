"""MinIO sync backend."""

from pathlib import Path
from typing import Optional

from dv.sync.base import SyncBackend


class MinIOBackend(SyncBackend):
    """MinIO backend (S3-compatible)."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = True,
        prefix: str = "dataveil/",
    ):
        try:
            from minio import Minio  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("minio is required for MinIO backend. pip install minio") from e

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket = bucket
        self.prefix = prefix

        # Ensure bucket exists
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}{remote_key}"

    def upload(self, local_path: Path, remote_key: str) -> bool:
        try:
            self.client.fput_object(self.bucket, self._key(remote_key), str(local_path))
            return True
        except Exception:
            return False

    def download(self, remote_key: str, local_path: Path) -> bool:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.fget_object(self.bucket, self._key(remote_key), str(local_path))
            return True
        except Exception:
            return False

    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        try:
            import io

            self.client.put_object(
                self.bucket,
                self._key(remote_key),
                io.BytesIO(data),
                len(data),
            )
            return True
        except Exception:
            return False

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(self.bucket, self._key(remote_key))
            return response.read()
        except Exception:
            return None

    def exists(self, remote_key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, self._key(remote_key))
            return True
        except Exception:
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        try:
            objects = self.client.list_objects(self.bucket, prefix=f"{self.prefix}{prefix}")
            return [obj.object_name for obj in objects]
        except Exception:
            return []
