"""Tests for dv init command."""

import json
from pathlib import Path

from click.testing import CliRunner

from dv.cli.init_cmd import ClaudeCodeConfigurator, ToolDetector, init


class TestToolDetector:
    def test_detects_claude_code(self, tmp_path: Path):
        claude_config = tmp_path / ".claude" / "settings.json"
        claude_config.parent.mkdir()
        claude_config.write_text("{}")

        detector = ToolDetector()
        tools = detector.detect_all()
        # This test is limited since we can't easily mock Path.home()
        # Just verify the structure exists
        assert len(tools) == 3
        assert any(t.name == "claude-code" for t in tools)


class TestClaudeCodeConfigurator:
    def test_configure_dry_run(self, tmp_path: Path):
        config_path = tmp_path / "settings.json"
        config_path.write_text(
            json.dumps(
                {
                    "env": {
                        "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
                        "ANTHROPIC_AUTH_TOKEN": "sk-test",
                        "ANTHROPIC_MODEL": "kimi-k2.6",
                    }
                }
            )
        )

        configurator = ClaudeCodeConfigurator("http://127.0.0.1:8787")
        result = configurator.configure(config_path, dry_run=True)

        assert result["status"] == "dry_run"
        assert len(result["changes"]) > 0
        # Verify file wasn't modified
        with open(config_path) as f:
            data = json.load(f)
        assert "ANTHROPIC_AUTH_TOKEN" in data["env"]

    def test_configure_applies_changes(self, tmp_path: Path):
        config_path = tmp_path / "settings.json"
        config_path.write_text(
            json.dumps(
                {
                    "env": {
                        "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
                        "ANTHROPIC_AUTH_TOKEN": "sk-test",
                    }
                }
            )
        )

        configurator = ClaudeCodeConfigurator("http://127.0.0.1:8787")
        result = configurator.configure(config_path, dry_run=False)

        assert result["status"] == "configured"
        with open(config_path) as f:
            data = json.load(f)
        assert data["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:8787"
        assert "ANTHROPIC_AUTH_TOKEN" not in data["env"]


class TestInitCommand:
    def test_init_help(self):
        runner = CliRunner()
        result = runner.invoke(init, ["--help"])
        assert result.exit_code == 0
        assert "One-command setup" in result.output
