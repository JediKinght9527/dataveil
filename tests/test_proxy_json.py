"""Regression tests for JSON-safe gateway transformations."""
import json

from dv.gateway.proxy import PrivacyProxy


def test_redaction_keeps_json_valid_near_escaped_content():
    proxy = object.__new__(PrivacyProxy)
    proxy.engine = __import__("dv.privacy.engine", fromlist=["PrivacyEngine"]).PrivacyEngine()
    body = json.dumps(
        {"messages": [{"content": r"literal \\ and marco@example.com"}]}
    ).encode()

    redacted, mapping = proxy._redact_json_body(body)

    payload = json.loads(redacted)
    assert "marco@example.com" not in payload["messages"][0]["content"]
    assert "<EMAIL_1>" in payload["messages"][0]["content"]
    assert mapping["<EMAIL_1>"] == "marco@example.com"
