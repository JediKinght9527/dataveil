"""Custom rule engine with YAML DSL support."""

from pathlib import Path
from typing import Any, Optional

import yaml

from dv.privacy.detector import SensitiveEntity
from dv.privacy.rules.base import BaseRule


class CustomRule(BaseRule):
    """User-defined rule from YAML DSL."""

    def __init__(self, rule_def: dict[str, Any]):
        self.name = rule_def.get("name", "custom")
        self._pattern = rule_def.get("pattern", "")
        self._entity_type = rule_def.get("entity_type", "custom")
        self._confidence = rule_def.get("confidence", 0.80)
        self._description = rule_def.get("description", "")

    def detect(self, text: str) -> list[SensitiveEntity]:
        import re

        entities: list[SensitiveEntity] = []
        try:
            pattern = re.compile(self._pattern, re.IGNORECASE)
            for m in pattern.finditer(text):
                entities.append(
                    SensitiveEntity(
                        start=m.start(),
                        end=m.end(),
                        text=m.group(),
                        entity_type=self._entity_type,
                        confidence=self._confidence,
                    )
                )
        except re.error:
            pass
        return entities


class CustomRuleEngine:
    """Load and manage custom rules from YAML files."""

    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or Path.home() / ".dataveil" / "rules.yaml"
        self._rules: list[CustomRule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        if not self.rules_path.exists():
            return
        try:
            with open(self.rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for rule_def in data.get("rules", []):
                self._rules.append(CustomRule(rule_def))
        except Exception:
            pass

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []
        for rule in self._rules:
            entities.extend(rule.detect(text))
        return entities

    def add_rule(self, rule_def: dict[str, Any]) -> None:
        """Add a new rule and persist to file."""
        self._rules.append(CustomRule(rule_def))
        self._save_rules()

    def _save_rules(self) -> None:
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"rules": [r.__dict__ for r in self._rules]}
        with open(self.rules_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def list_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name,
                "pattern": r._pattern,
                "entity_type": r._entity_type,
                "confidence": r._confidence,
                "description": r._description,
            }
            for r in self._rules
        ]
