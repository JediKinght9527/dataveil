"""AWS S3 sync backend."""

from pathlib import Path
from typing import Optional

from dv.sync.base import SyncBackend


class S3Backend(SyncBackend):
    """AWS S3 backend using boto3."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        prefix: str = "dataveil/",
    ):
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("boto3 is required for S3 backend. pip install boto3") from e

        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        self.bucket = bucket
        self.prefix = prefix

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}{remote_key}"

    def upload(self, local_path: Path, remote_key: str) -> bool:
        try:
            self.client.upload_file(str(local_path), self.bucket, self._key(remote_key))
            return True
        except Exception:
            return False

    def download(self, remote_key: str, local_path: Path) -> bool:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.bucket, self._key(remote_key), str(local_path))
            return True
        except Exception:
            return False

    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        try:
            self.client.put_object(Bucket=self.bucket, Key=self._key(remote_key), Body=data)
            return True
        except Exception:
            return False

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(remote_key))
            return response["Body"].read()
        except Exception:
            return None

    def exists(self, remote_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(remote_key))
            return True
        except Exception:
            return False

    def list_objects(self, prefix: str = "") -> list[str]:
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}{prefix}"
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception:
            return []
