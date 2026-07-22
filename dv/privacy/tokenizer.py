"""Semantic placeholder generation."""
from __future__ import annotations


class Tokenizer:
    """Generate semantic placeholders like <EMAIL_1>, <API_KEY_2>."""

    _counters: dict[str, int] = {}

    @classmethod
    def tokenize(cls, entity_type: str, index: int) -> str:
        return f"<{entity_type.upper()}_{index}>"

    @classmethod
    def reset(cls) -> None:
        cls._counters.clear()
