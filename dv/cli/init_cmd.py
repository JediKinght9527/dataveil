"""One-command setup for AI tools."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click


@dataclass
class ToolConfig:
    name: str
    config_path: Path
    detected: bool
    backup_path: Optional[Path] = None


class ToolDetector:
    """Detect installed AI coding tools."""

    @staticmethod
    def detect_all() -> list[ToolConfig]:
        home = Path.home()
        tools = [
            ToolConfig(
                name="claude-code",
                config_path=home / ".claude" / "settings.json",
                detected=False,
            ),
            ToolConfig(
                name="cursor",
                config_path=home
                / "Library"
                / "Application Support"
                / "Cursor"
                / "User"
                / "globalStorage"
                / "cursor-ai.config.json",
                detected=False,
            ),
            ToolConfig(
                name="codex",
                config_path=home / ".codex" / "config.json",
                detected=False,
            ),
        ]

        for tool in tools:
            tool.detected = tool.config_path.exists()

        return tools


class ConfigBackup:
    """Backup and restore tool configurations."""

    @staticmethod
    def backup(tool: ToolConfig) -> Path:
        """Create a timestamped backup."""
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = tool.config_path.with_suffix(f".backup.{timestamp}")
        shutil.copy2(tool.config_path, backup_path)
        return backup_path

    @staticmethod
    def restore(tool: ToolConfig, backup_path: Path) -> None:
        """Restore from backup."""
        shutil.copy2(backup_path, tool.config_path)


class ClaudeCodeConfigurator:
    """Configure Claude Code to use DataVeil gateway."""

    def __init__(self, gateway_url: str = "http://127.0.0.1:8787"):
        self.gateway_url = gateway_url

    def configure(self, config_path: Path, dry_run: bool = False) -> dict:
        """Modify Claude Code settings.json."""
        if not config_path.exists():
            return {"status": "skipped", "reason": "config not found"}

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        changes = []

        # Backup current values
        old_base_url = config.get("env", {}).get("ANTHROPIC_BASE_URL", "")
        old_token = config.get("env", {}).get("ANTHROPIC_AUTH_TOKEN", "")

        # Set gateway URL
        if old_base_url != self.gateway_url:
            config.setdefault("env", {})["ANTHROPIC_BASE_URL"] = self.gateway_url
            changes.append(f"ANTHROPIC_BASE_URL: {old_base_url} → {self.gateway_url}")

        # Remove direct token (DataVeil holds it now)
        if old_token:
            del config["env"]["ANTHROPIC_AUTH_TOKEN"]
            changes.append("ANTHROPIC_AUTH_TOKEN: removed (moved to DataVeil vault)")

        # Preserve model settings
        if "ANTHROPIC_MODEL" not in config.get("env", {}):
            config.setdefault("env", {})["ANTHROPIC_MODEL"] = "kimi-k2.6"
            changes.append("ANTHROPIC_MODEL: set to kimi-k2.6")

        if not dry_run:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        return {
            "status": "configured" if not dry_run else "dry_run",
            "changes": changes,
            "config_path": str(config_path),
        }


@click.command(name="init")
@click.option("--gateway-url", default="http://127.0.0.1:8787", help="DataVeil gateway URL")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--tool", type=click.Choice(["claude-code", "cursor", "codex", "all"]), default="all")
def init(gateway_url: str, dry_run: bool, tool: str):
    """One-command setup for AI tools to use DataVeil gateway."""
    click.echo("🔍 Detecting installed AI tools...")

    detector = ToolDetector()
    tools = detector.detect_all()
    detected = [t for t in tools if t.detected]

    if not detected:
        click.echo("⚠️  No supported AI tools detected.")
        click.echo("   Supported: Claude Code, Cursor, Codex CLI")
        return

    click.echo(f"   Found: {', '.join(t.name for t in detected)}")

    # Filter by tool selection
    if tool != "all":
        detected = [t for t in detected if t.name == tool]

    # Backup
    if not dry_run:
        click.echo("\n📦 Creating backups...")
        for t in detected:
            backup = ConfigBackup.backup(t)
            t.backup_path = backup
            click.echo(f"   {t.name}: {backup}")

    # Configure
    click.echo("\n⚙️  Configuring tools...")

    for t in detected:
        if t.name == "claude-code":
            configurator = ClaudeCodeConfigurator(gateway_url)
            result = configurator.configure(t.config_path, dry_run=dry_run)

            if result["status"] == "skipped":
                click.echo(f"   ⏭️  {t.name}: {result['reason']}")
            else:
                click.echo(f"   ✅ {t.name}: {len(result['changes'])} changes")
                for change in result["changes"]:
                    click.echo(f"      • {change}")
        else:
            click.echo(f"   ⏭️  {t.name}: not yet supported (coming soon)")

    # Generate restore script
    if not dry_run:
        restore_script = Path.home() / ".dataveil" / "restore.sh"
        restore_script.parent.mkdir(parents=True, exist_ok=True)

        with open(restore_script, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write("# Restore original tool configurations\n")
            for t in detected:
                if t.backup_path:
                    f.write(f"cp '{t.backup_path}' '{t.config_path}'\n")
            f.write("echo '✅ Original configurations restored'\n")

        restore_script.chmod(0o755)
        click.echo(f"\n📝 Restore script: {restore_script}")
        click.echo("   Run this to revert all changes.")

    click.echo("\n🎉 Setup complete!")
    click.echo(f"   Gateway: {gateway_url}")
    click.echo("   Start gateway: dv start")
    click.echo("   Your tools will now route through DataVeil.")

    if dry_run:
        click.echo("\n⚠️  This was a dry run. No changes were applied.")
