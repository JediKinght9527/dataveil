"""Auto-detect project info from git remotes."""

import re
import subprocess

from dv.privacy.detector import SensitiveEntity
from dv.privacy.rules.base import BaseRule


class GitRule(BaseRule):
    """Detect project/org names from git remotes."""

    name = "git"

    def detect(self, text: str) -> list[SensitiveEntity]:
        # MVP: simple heuristic based on git remote output
        # Future: cache remote hosts and match against text
        return []

    @staticmethod
    def get_remote_hosts() -> list[str]:
        """Extract hostnames from git remotes in current directory."""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            hosts = set()
            for line in result.stdout.splitlines():
                match = re.search(r"@([\w.-]+)[:/]", line)
                if match:
                    hosts.add(match.group(1))
            return list(hosts)
        except Exception:
            return []
