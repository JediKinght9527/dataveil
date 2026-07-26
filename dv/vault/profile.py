"""Multi-profile key management."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    provider: str
    base_url: str


DEFAULT_PROFILES = {
    "kimi": Profile(
        name="kimi",
        provider="kimi",
        base_url="https://api.moonshot.cn/anthropic",
    ),
    "openai": Profile(
        name="openai",
        provider="openai",
        base_url="https://api.openai.com/v1",
    ),
    "anthropic": Profile(
        name="anthropic",
        provider="anthropic",
        base_url="https://api.anthropic.com/v1",
    ),
}
