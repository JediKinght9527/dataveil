"""S3 sync placeholder (AWS S3)."""
from dv.sync.base import SyncBackend


class S3Backend(SyncBackend):
    """AWS S3 sync backend (Pro feature)."""

    def upload(self, local_path, remote_key):
        raise NotImplementedError("S3 sync requires Pro license")

    def download(self, remote_key, local_path):
        raise NotImplementedError("S3 sync requires Pro license")
