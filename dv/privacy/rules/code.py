"""Code-aware detection rules."""
import re

from dv.privacy.detector import SensitiveEntity
from dv.privacy.rules.base import BaseRule


class CodeRule(BaseRule):
    """Detect code-specific sensitive patterns."""

    name = "code"

    ENV_KEY_PATTERN = re.compile(
        r"\b([A-Z_]*(?:SECRET|KEY|TOKEN|PWD|PASSWORD|API_KEY|ACCESS_KEY)[A-Z_]*)\s*=\s*['\"]?[^\s'\"]+",
        re.IGNORECASE,
    )

    TODO_LEAK_PATTERN = re.compile(
        r"//\s*TODO[:\s]+.*(?:client|customer|internal|secret|fix\s+before)",
        re.IGNORECASE,
    )

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []
        for m in self.ENV_KEY_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="env_secret",
                    confidence=0.90,
                )
            )
        for m in self.TODO_LEAK_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="todo_leak",
                    confidence=0.75,
                )
            )
        return entities
