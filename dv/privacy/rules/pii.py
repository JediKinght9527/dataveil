"""General PII detection rules."""

from dv.privacy.detector import SensitiveEntity
from dv.privacy.rules.base import BaseRule


class PIIRule(BaseRule):
    """Placeholder for ML-based PII detection (future)."""

    name = "pii"

    def detect(self, text: str) -> list[SensitiveEntity]:
        # For MVP, the base Detector handles regex PII.
        # This rule预留s for Presidio/spaCy integration.
        return []
