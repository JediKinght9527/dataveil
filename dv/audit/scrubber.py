"""Scrub sensitive data from audit logs before export."""
import re


class LogScrubber:
    """Remove or hash potentially sensitive fields in log entries."""

    @staticmethod
    def scrub(text: str) -> str:
        # Simple heuristic: remove anything that looks like an API key
        return re.sub(r"sk-\w{24,}", "[SCRUBBED]", text)
