"""Tests for Privacy Engine detection and tokenization."""
from dv.privacy.detector import Detector
from dv.privacy.engine import PrivacyEngine
from dv.privacy.tokenizer import Tokenizer


class TestDetector:
    def test_detect_email(self):
        d = Detector()
        entities = d.detect("Contact me at marco@example.com please")
        assert len(entities) == 1
        assert entities[0].entity_type == "email"
        assert entities[0].text == "marco@example.com"

    def test_detect_phone(self):
        d = Detector()
        entities = d.detect("Call 13800138000 for support")
        assert len(entities) == 1
        assert entities[0].entity_type == "phone"

    def test_detect_api_key(self):
        d = Detector()
        entities = d.detect("Key: sk-live-abcdefghijklmnopqrstuvwxyz")
        assert len(entities) == 1
        assert entities[0].entity_type == "api_key"

    def test_detect_internal_domain(self):
        d = Detector()
        entities = d.detect("Visit https://internal-api.alipay.com/v1")
        assert len(entities) >= 1
        assert any(e.entity_type == "internal_domain" for e in entities)

    def test_no_false_positives(self):
        d = Detector()
        entities = d.detect("The quick brown fox jumps over the lazy dog")
        assert len(entities) == 0


class TestTokenizer:
    def test_tokenize(self):
        assert Tokenizer.tokenize("email", 1) == "<EMAIL_1>"
        assert Tokenizer.tokenize("api_key", 2) == "<API_KEY_2>"


class TestPrivacyEngine:
    def test_process(self):
        engine = PrivacyEngine()
        text = "Email marco@example.com and call 13800138000"
        replaced, mapping = engine.process(text)
        assert "<EMAIL_1>" in replaced
        assert "<PHONE_1>" in replaced
        assert "marco@example.com" not in replaced
        assert "13800138000" not in replaced
        assert mapping["<EMAIL_1>"] == "marco@example.com"
        assert mapping["<PHONE_1>"] == "13800138000"

    def test_restore(self):
        engine = PrivacyEngine()
        mapping = {"<EMAIL_1>": "marco@example.com"}
        restored = engine.restore("Contact <EMAIL_1> please", mapping)
        assert restored == "Contact marco@example.com please"

    def test_empty_text(self):
        engine = PrivacyEngine()
        replaced, mapping = engine.process("")
        assert replaced == ""
        assert mapping == {}
