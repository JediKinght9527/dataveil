"""Tencent COS sync backend."""
from pathlib import Path
from typing import Optional

from dv.sync.base import SyncBackend


class COSBackend(SyncBackend):
    """Tencent COS backend using cos-python-sdk-v5."""

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        bucket: str,
        region: str,
        prefix: str = "dataveil/",
    ):
        try:
            from qcloud_cos import CosConfig, CosS3Client  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "cos-python-sdk-v5 is required for Tencent COS. pip install cos-python-sdk-v5"
            ) from e

        config = CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
        )
        self.client = CosS3Client(config)
        self.bucket = bucket
        self.prefix = prefix

    def _key(self, remote_key: str) -> str:
        return f"{self.prefix}{remote_key}"

    def upload(self, local_path: Path, remote_key: str) -> bool:
        try:
            self.client.upload_file(
                Bucket=self.bucket,
                LocalFilePath=str(local_path),
                Key=self._key(remote_key),
            )
            return True
        except Exception:
            return False

    def download(self, remote_key: str, local_path: Path) -> bool:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(
                Bucket=self.bucket,
                Key=self._key(remote_key),
                DestFilePath=str(local_path),
            )
            return True
        except Exception:
            return False

    def upload_bytes(self, data: bytes, remote_key: str) -> bool:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Body=data,
                Key=self._key(remote_key),
            )
            return True
        except Exception:
            return False

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=self._key(remote_key),
            )
            return response["Body"].get_raw_stream().read()
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
            response = self.client.list_objects(
                Bucket=self.bucket,
                Prefix=f"{self.prefix}{prefix}",
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception:
            return []
