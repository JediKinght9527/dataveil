"""Stream rehydration: restore original data from placeholders."""
import json
import re
from typing import Dict, Iterator


class Rehydrator:
    """Replace placeholders with original values in text or SSE streams."""

    def __init__(self, mapping: Dict[str, str]):
        """
        mapping: {<EMAIL_1>: "marco@example.com", ...}
        """
        self.mapping = mapping
        if mapping:
            self._pattern = re.compile("|".join(re.escape(k) for k in mapping.keys()))
        else:
            self._pattern = None

    def rehydrate_text(self, text: str) -> str:
        if not self._pattern:
            return text
        return self._pattern.sub(lambda m: self.mapping.get(m.group(), m.group()), text)

    def rehydrate_sse_stream(self, lines: Iterator[str]) -> Iterator[str]:
        """
        SSE format: data: {...}\n\n
        Only replace inside JSON content to preserve framing.
        """
        for line in lines:
            if line.startswith("data: "):
                payload = line[6:]
                try:
                    data = json.loads(payload)
                    # OpenAI/Anthropic SSE shape
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {})
                        if "content" in delta and isinstance(delta["content"], str):
                            delta["content"] = self.rehydrate_text(delta["content"])
                        # Anthropic format
                        if "text" in delta and isinstance(delta["text"], str):
                            delta["text"] = self.rehydrate_text(delta["text"])
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    yield line
            else:
                yield line

    def rehydrate_json(self, data: dict) -> dict:
        """Rehydrate a full JSON response body."""
        text = json.dumps(data)
        rehydrated = self.rehydrate_text(text)
        return json.loads(rehydrated)
