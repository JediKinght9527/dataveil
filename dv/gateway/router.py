"""Multi-provider routing logic."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRoute:
    name: str
    base_url: str
    chat_path: str = "/v1/chat/completions"
    models_path: str = "/v1/models"


ROUTES = {
    "kimi": ProviderRoute(
        name="kimi",
        base_url="https://api.moonshot.cn/anthropic",
        chat_path="/v1/messages",
    ),
    "openai": ProviderRoute(
        name="openai",
        base_url="https://api.openai.com/v1",
    ),
    "anthropic": ProviderRoute(
        name="anthropic",
        base_url="https://api.anthropic.com/v1",
        chat_path="/v1/messages",
    ),
}
