"""Tests for enhanced code-aware rules."""

from pathlib import Path

from dv.privacy.rules.code import CodeRule, EnvFileRule
from dv.privacy.rules.custom import CustomRuleEngine


class TestCodeRule:
    def test_detect_env_secret(self):
        rule = CodeRule()
        entities = rule.detect("DATABASE_PASSWORD=secret123")
        assert len(entities) == 1
        assert entities[0].entity_type == "env_secret"

    def test_detect_sql_connection(self):
        rule = CodeRule()
        entities = rule.detect("Connect to mysql://user:pass@localhost/db")
        assert len(entities) == 1
        assert entities[0].entity_type == "sql_connection"

    def test_detect_jwt(self):
        rule = CodeRule()
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        )
        entities = rule.detect(f"Token: {jwt}")
        assert len(entities) == 1
        assert entities[0].entity_type == "jwt_token"

    def test_detect_ssh_key(self):
        rule = CodeRule()
        entities = rule.detect("-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...")
        assert len(entities) == 1
        assert entities[0].entity_type == "ssh_private_key"

    def test_detect_internal_path(self):
        rule = CodeRule()
        entities = rule.detect("Call /api/v1/internal/users endpoint")
        assert len(entities) >= 1
        assert any(e.entity_type == "internal_path" for e in entities)


class TestEnvFileRule:
    def test_loads_env_keys(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgres://localhost\nAPI_KEY=secret\n")
        rule = EnvFileRule(env_path=env_file)
        entities = rule.detect("Use DATABASE_URL and API_KEY in config")
        assert len(entities) == 2
        assert all(e.entity_type == "env_key_name" for e in entities)

    def test_missing_env_file(self, tmp_path: Path):
        rule = EnvFileRule(env_path=tmp_path / "nonexistent.env")
        entities = rule.detect("DATABASE_URL")
        assert len(entities) == 0


class TestCustomRuleEngine:
    def test_load_rules(self, tmp_path: Path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - name: internal-project
    pattern: "PROJECT_[A-Z]+"
    entity_type: internal_project
    confidence: 0.9
    description: "Internal project codenames"
""")
        engine = CustomRuleEngine(rules_path=rules_file)
        entities = engine.detect("Working on PROJECT_ALPHA and PROJECT_BETA")
        assert len(entities) == 2
        assert all(e.entity_type == "internal_project" for e in entities)

    def test_add_rule(self, tmp_path: Path):
        rules_file = tmp_path / "rules.yaml"
        engine = CustomRuleEngine(rules_path=rules_file)
        engine.add_rule(
            {
                "name": "test-rule",
                "pattern": r"\btest\d+\b",
                "entity_type": "test_pattern",
                "confidence": 0.8,
            }
        )
        entities = engine.detect("This is test123 and test456")
        assert len(entities) == 2
