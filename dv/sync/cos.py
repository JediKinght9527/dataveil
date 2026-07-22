"""COS sync placeholder (Tencent COS)."""
from dv.sync.base import SyncBackend


class COSBackend(SyncBackend):
    """Tencent COS sync backend (Pro feature)."""

    def upload(self, local_path, remote_key):
        raise NotImplementedError("COS sync requires Pro license")

    def download(self, remote_key, local_path):
        raise NotImplementedError("COS sync requires Pro license")
