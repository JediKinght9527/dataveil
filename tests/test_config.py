"""Tests for configuration system."""

from pathlib import Path

from dv.config import ConfigLoader


class TestConfigLoader:
    def test_defaults(self):
        loader = ConfigLoader()
        config = loader.load()
        assert config.gateway.host == "127.0.0.1"
        assert config.gateway.port == 8787
        assert config.audit.enabled is True
        assert config.privacy.mode == "transparent"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DV_GATEWAY_PORT", "9999")
        monkeypatch.setenv("DV_PRIVACY_MODE", "strict")
        loader = ConfigLoader()
        config = loader.load()
        assert config.gateway.port == 9999
        assert config.privacy.mode == "strict"

    def test_global_config_file(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
gateway:
  port: 7777
audit:
  retention_days: 7
""")
        loader = ConfigLoader()
        loader.DEFAULT_CONFIG_PATH = config_file
        config = loader.load()
        assert config.gateway.port == 7777
        assert config.audit.retention_days == 7

    def test_project_config_override(self, tmp_path: Path):
        # Create global config
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir()
        global_config.write_text("""
gateway:
  port: 7777
""")

        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".dataveilrc"
        project_config.write_text("""
gateway:
  port: 8888
""")

        loader = ConfigLoader()
        loader.DEFAULT_CONFIG_PATH = global_config
        config = loader.load(project_root=project_dir)
        # Project config should override global
        assert config.gateway.port == 8888

    def test_deep_merge(self):
        loader = ConfigLoader()
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 3, "d": 4}}
        result = loader._deep_merge(base, override)
        assert result == {"a": {"b": 3, "c": 2, "d": 4}}
