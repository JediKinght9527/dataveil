"""OSS sync placeholder (Aliyun OSS)."""
from dv.sync.base import SyncBackend


class OSSBackend(SyncBackend):
    """Aliyun OSS sync backend (Pro feature)."""

    def upload(self, local_path, remote_key):
        raise NotImplementedError("OSS sync requires Pro license")

    def download(self, remote_key, local_path):
        raise NotImplementedError("OSS sync requires Pro license")
