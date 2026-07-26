"""
Configuration system with layered priority:
  env vars > project .dataveilrc > ~/.dataveil/config.yaml > defaults
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class SyncConfig(BaseModel):
    enabled: bool = False
    provider: str = "oss"  # oss, s3, cos, minio
    bucket: str = ""
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = ""
    encrypt: bool = True
    interval_seconds: int = 300


class AuditConfig(BaseModel):
    # Disabled by default: audit logs are a second copy of request metadata.
    # Opt in explicitly with audit.enabled=true or DV_AUDIT_ENABLED=1.
    enabled: bool = False
    log_path: Path = Field(default_factory=lambda: Path.home() / ".dataveil" / "audit.jsonl")
    retention_days: int = 30
    scrub_sensitive: bool = True
    sync_to_oss: bool = False


class GatewayConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787
    default_profile: str = "default"
    cors_origins: list[str] = ["*"]
    max_request_size: int = 10 * 1024 * 1024  # 10MB


class VaultConfig(BaseModel):
    path: Path = Field(default_factory=lambda: Path.home() / ".dataveil" / "vault.db")
    keyring_service: str = "dataveil"
    keyring_account: str = "vault"
    auto_lock_minutes: int = 60


class PrivacyConfig(BaseModel):
    mode: str = "transparent"  # transparent, strict
    enabled_rules: list[str] = ["code", "pii", "git"]
    custom_rules_path: Optional[Path] = None
    confidence_threshold: float = 0.80


class Config(BaseModel):
    """Root configuration model."""

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    vault: VaultConfig = Field(default_factory=VaultConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


class ConfigLoader:
    """Load and merge configuration from multiple sources."""

    DEFAULT_CONFIG_PATH = Path.home() / ".dataveil" / "config.yaml"
    PROJECT_CONFIG_NAMES = (".dataveilrc", ".dataveil.yaml", ".dataveil.yml")

    def __init__(self) -> None:
        self._config: Optional[Config] = None
        self._project_root: Optional[Path] = None

    def load(self, project_root: Optional[Path] = None) -> Config:
        """Load config with layered priority."""
        self._project_root = project_root or Path.cwd()

        # Layer 1: defaults
        data: dict[str, Any] = {}

        # Layer 2: global config file
        global_data = self._load_yaml(self.DEFAULT_CONFIG_PATH)
        if global_data:
            data = self._deep_merge(data, global_data)

        # Layer 3: project config file
        project_config = self._find_project_config()
        if project_config:
            project_data = self._load_yaml(project_config)
            if project_data:
                data = self._deep_merge(data, project_data)

        # Layer 4: environment variables
        env_data = self._load_env()
        if env_data:
            data = self._deep_merge(data, env_data)

        self._config = Config(**data)
        return self._config

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    def _find_project_config(self) -> Optional[Path]:
        """Walk up from project root to find config file."""
        if not self._project_root:
            return None
        current = self._project_root.resolve()
        for parent in [current, *current.parents]:
            for name in self.PROJECT_CONFIG_NAMES:
                candidate = parent / name
                if candidate.exists():
                    return candidate
        return None

    def _load_env(self) -> dict[str, Any]:
        """Load config from DV_* environment variables."""
        data: dict[str, Any] = {}

        # Map env vars to nested config paths
        env_map = {
            "DV_GATEWAY_HOST": ("gateway", "host"),
            "DV_GATEWAY_PORT": ("gateway", "port"),
            "DV_DEFAULT_PROFILE": ("gateway", "default_profile"),
            "DV_VAULT_PATH": ("vault", "path"),
            "DV_AUDIT_ENABLED": ("audit", "enabled"),
            "DV_AUDIT_LOG_PATH": ("audit", "log_path"),
            "DV_SYNC_ENABLED": ("sync", "enabled"),
            "DV_SYNC_PROVIDER": ("sync", "provider"),
            "DV_SYNC_BUCKET": ("sync", "bucket"),
            "DV_PRIVACY_MODE": ("privacy", "mode"),
        }

        for env_key, (section, key) in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                if section not in data:
                    data[section] = {}
                # Type coercion
                coerced: Any = value
                if key in ("port", "interval_seconds", "retention_days", "auto_lock_minutes"):
                    coerced = int(value)
                elif key in ("enabled", "encrypt", "sync_to_oss", "scrub_sensitive"):
                    coerced = value.lower() in ("1", "true", "yes", "on")
                elif key == "confidence_threshold":
                    coerced = float(value)
                data[section][key] = coerced

        return data

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge two dicts."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save_global(self, config: Config) -> None:
        """Save config to global config file."""
        self.DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)

    @property
    def config(self) -> Config:
        if self._config is None:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self._config


# Singleton loader
_loader = ConfigLoader()


def load_config(project_root: Optional[Path] = None) -> Config:
    """Load configuration (convenience wrapper)."""
    return _loader.load(project_root)


def get_config() -> Config:
    """Get already-loaded config."""
    return _loader.config
