"""Pydantic settings for DataVeil."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DV_",
        env_file="~/.dataveil/env",
        env_file_encoding="utf-8",
    )

    vault_path: Path = Path.home() / ".dataveil" / "vault.db"
    vault_password: str = ""  # Interactive fallback
    config_path: Path = Path.home() / ".dataveil" / "config.yaml"
    default_profile: str = "default"
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 8787
    audit_log_path: Path = Path.home() / ".dataveil" / "audit.jsonl"
    audit_enabled: bool = True


def get_settings() -> Settings:
    return Settings()
