"""Base rule interface for pluggable detection rules."""
from abc import ABC, abstractmethod
from typing import List

from dv.privacy.detector import SensitiveEntity


class BaseRule(ABC):
    """Abstract base for custom detection rules."""

    name: str = ""

    @abstractmethod
    def detect(self, text: str) -> List[SensitiveEntity]:
        ...
