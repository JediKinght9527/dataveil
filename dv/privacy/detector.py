"""
Multi-layer detector: Regex (fast) → NER (smart) → Code-Aware (contextual)
"""
import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitiveEntity:
    start: int
    end: int
    text: str
    entity_type: str
    confidence: float


class Detector:
    """Detect sensitive entities in text with code-aware rules."""

    PATTERNS = {
        "internal_domain": re.compile(
            r"(https?://)?(?:[a-z0-9-]+\.)*(?:internal|corp|intranet|gitlab|jenkins|nexus|harbor|k8s|kube|aliyun|tencent)[a-z0-9-]*\.[a-z]{2,}",
            re.IGNORECASE,
        ),
        "api_key": re.compile(
            r"\b(sk-(?:live|test|prod|ant|kimi|proj)-[a-zA-Z0-9]{24,})\b",
            re.IGNORECASE,
        ),
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "phone": re.compile(r"(?:\+?86)?1[3-9]\d{9}"),
        "ip_address": re.compile(
            r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}\b"
        ),
        "file_path": re.compile(
            r"(/Users/[^/]+/[^\s]+|/home/[^/]+/[^\s]+|C:\\\\Users\\\\[^\\\\]+\\\\[^\s]+)",
        ),
    }

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []
        seen_spans: set[tuple[int, int]] = set()

        for entity_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                confidence = 0.95 if entity_type in ("email", "phone", "api_key") else 0.85
                entities.append(
                    SensitiveEntity(
                        start=match.start(),
                        end=match.end(),
                        text=match.group(),
                        entity_type=entity_type,
                        confidence=confidence,
                    )
                )
        return sorted(entities, key=lambda e: e.start)

    @staticmethod
    def hash_entity(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
