"""Privacy engine orchestrator: detect → replace → rehydrate."""
from typing import Dict, List

from .detector import Detector, SensitiveEntity
from .tokenizer import Tokenizer
from .rehydrator import Rehydrator


class PrivacyEngine:
    """Orchestrate detection, tokenization, and rehydration."""

    def __init__(self) -> None:
        self.detector = Detector()

    def process(self, text: str) -> tuple[str, Dict[str, str]]:
        """
        Replace sensitive entities with semantic placeholders.
        Returns (replaced_text, mapping).
        """
        entities = self.detector.detect(text)

        # First pass: assign tokens in forward order
        entity_tokens: list[tuple[SensitiveEntity, str]] = []
        type_counters: Dict[str, int] = {}
        for ent in entities:
            type_counters[ent.entity_type] = type_counters.get(ent.entity_type, 0) + 1
            token = Tokenizer.tokenize(ent.entity_type, type_counters[ent.entity_type])
            entity_tokens.append((ent, token))

        # Second pass: replace from end to start so indices don't shift
        replaced = text
        for ent, token in reversed(entity_tokens):
            replaced = replaced[: ent.start] + token + replaced[ent.end :]

        mapping = {token: ent.text for ent, token in entity_tokens}
        return replaced, mapping

    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        return Rehydrator(mapping).rehydrate_text(text)

    def restore_stream(self, lines, mapping: Dict[str, str]):
        return Rehydrator(mapping).rehydrate_sse_stream(lines)

    def restore_json(self, data: dict, mapping: Dict[str, str]) -> dict:
        return Rehydrator(mapping).rehydrate_json(data)
