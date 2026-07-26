"""Enhanced code-aware detection rules."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from dv.privacy.detector import SensitiveEntity
from dv.privacy.rules.base import BaseRule


class CodeRule(BaseRule):
    """Detect code-specific sensitive patterns."""

    name = "code"

    ENV_KEY_PATTERN = re.compile(
        r"\b([A-Z_]*(?:SECRET|KEY|TOKEN|PWD|PASSWORD|API_KEY|ACCESS_KEY)[A-Z_]*)\s*=\s*['\"]?[^\s'\"]+",
        re.IGNORECASE,
    )

    TODO_LEAK_PATTERN = re.compile(
        r"//\s*TODO[:\s]+.*(?:client|customer|internal|secret|fix\s+before|temporary)",
        re.IGNORECASE,
    )

    # SQL connection strings
    SQL_CONN_PATTERN = re.compile(
        r"(?:mysql|postgres|postgresql|mongodb|redis)://[^\s]+",
        re.IGNORECASE,
    )

    # JWT tokens
    JWT_PATTERN = re.compile(
        r"\beyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*\b",
    )

    # SSH private keys
    SSH_KEY_PATTERN = re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    )

    # Internal URL paths (not just domains)
    INTERNAL_PATH_PATTERN = re.compile(
        r"(?:/api/v\d+/|/internal/|/admin/|/manage/)[^\s\"']+",
        re.IGNORECASE,
    )

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []

        for m in self.ENV_KEY_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="env_secret",
                    confidence=0.90,
                )
            )

        for m in self.TODO_LEAK_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="todo_leak",
                    confidence=0.75,
                )
            )

        for m in self.SQL_CONN_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="sql_connection",
                    confidence=0.95,
                )
            )

        for m in self.JWT_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="jwt_token",
                    confidence=0.90,
                )
            )

        for m in self.SSH_KEY_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="ssh_private_key",
                    confidence=0.99,
                )
            )

        for m in self.INTERNAL_PATH_PATTERN.finditer(text):
            entities.append(
                SensitiveEntity(
                    start=m.start(),
                    end=m.end(),
                    text=m.group(),
                    entity_type="internal_path",
                    confidence=0.80,
                )
            )

        return entities


class EnvFileRule(BaseRule):
    """Auto-detect and protect env variable names from .env files."""

    name = "env_file"

    def __init__(self, env_path: Optional[Path] = None):
        self.env_path = env_path or Path.cwd() / ".env"
        self._key_names: set[str] = set()
        self._load_env_keys()

    def _load_env_keys(self) -> None:
        if not self.env_path.exists():
            return
        try:
            with open(self.env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        if key:
                            self._key_names.add(key)
        except OSError:
            pass

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []
        for key in self._key_names:
            # Match the key name as a whole word
            pattern = re.compile(rf"\b{re.escape(key)}\b")
            for m in pattern.finditer(text):
                entities.append(
                    SensitiveEntity(
                        start=m.start(),
                        end=m.end(),
                        text=m.group(),
                        entity_type="env_key_name",
                        confidence=0.85,
                    )
                )
        return entities


class GitRemoteRule(BaseRule):
    """Auto-detect project/org names from git remotes."""

    name = "git_remote"

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self._hosts: set[str] = set()
        self._orgs: set[str] = set()
        self._load_git_info()

    def _load_git_info(self) -> None:
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.repo_path,
            )
            for line in result.stdout.splitlines():
                # git@github.com:org/repo.git
                match = re.search(r"@([\w.-]+)[:/]([^/]+)/", line)
                if match:
                    self._hosts.add(match.group(1))
                    self._orgs.add(match.group(2))
                # https://github.com/org/repo.git
                match = re.search(r"https?://([\w.-]+)/([^/]+)/", line)
                if match:
                    self._hosts.add(match.group(1))
                    self._orgs.add(match.group(2))
        except Exception:
            pass

    def detect(self, text: str) -> list[SensitiveEntity]:
        entities: list[SensitiveEntity] = []

        for host in self._hosts:
            pattern = re.compile(rf"\b{re.escape(host)}\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                entities.append(
                    SensitiveEntity(
                        start=m.start(),
                        end=m.end(),
                        text=m.group(),
                        entity_type="git_host",
                        confidence=0.90,
                    )
                )

        for org in self._orgs:
            pattern = re.compile(rf"\b{re.escape(org)}\b")
            for m in pattern.finditer(text):
                entities.append(
                    SensitiveEntity(
                        start=m.start(),
                        end=m.end(),
                        text=m.group(),
                        entity_type="git_org",
                        confidence=0.85,
                    )
                )

        return entities
