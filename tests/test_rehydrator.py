"""Tests for stream rehydration."""

import json

from dv.privacy.rehydrator import Rehydrator


class TestRehydrator:
    def test_rehydrate_text(self):
        r = Rehydrator({"<EMAIL_1>": "a@b.com"})
        assert r.rehydrate_text("Hi <EMAIL_1>") == "Hi a@b.com"

    def test_rehydrate_text_no_match(self):
        r = Rehydrator({})
        assert r.rehydrate_text("No placeholders") == "No placeholders"

    def test_rehydrate_sse_stream(self):
        r = Rehydrator({"<NAME_1>": "Alice"})
        data = {"choices": [{"delta": {"content": "Hello <NAME_1>"}}]}
        lines = [f"data: {json.dumps(data)}\n\n"]
        result = list(r.rehydrate_sse_stream(iter(lines)))
        assert "Alice" in result[0]
        assert "<NAME_1>" not in result[0]

    def test_rehydrate_json(self):
        r = Rehydrator({"<KEY_1>": "secret"})
        data = {"message": "Use <KEY_1>"}
        result = r.rehydrate_json(data)
        assert result["message"] == "Use secret"

    def test_restore_json_preserves_backslashes(self):
        from dv.privacy.engine import PrivacyEngine

        data = {"message": r"Use \\<EMAIL_1>"}
        result = PrivacyEngine().restore_json(data, {"<EMAIL_1>": "a@b.com"})
        encoded = json.dumps(result)
        assert json.loads(encoded)["message"] == r"Use \\a@b.com"
