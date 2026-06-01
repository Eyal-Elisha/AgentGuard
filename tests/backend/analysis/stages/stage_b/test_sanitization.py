"""Stage B — sanitization & text-extraction tests."""

from backend.analysis.stages.stage_b.sanitization import (
    extract_semantic_text,
    sanitize,
)

from helpers import make_features


class TestSanitize:
    def test_redacts_email(self):
        assert "alice@example.com" not in sanitize("Contact alice@example.com please")

    def test_redacts_credit_card_like_run(self):
        assert "4242 4242 4242 4242" not in sanitize("Card 4242 4242 4242 4242 thanks")

    def test_redacts_password_assignment(self):
        cleaned = sanitize("password=hunter2 next field")
        assert "hunter2" not in cleaned
        assert "<REDACTED>" in cleaned

    def test_redacts_bearer_token(self):
        cleaned = sanitize("Authorization: Bearer abc.def.ghi123")
        assert "abc.def.ghi123" not in cleaned

    def test_handles_empty(self):
        assert sanitize("") == ""
        assert sanitize(None) == ""


class TestExtractSemanticText:
    def test_strips_script_tags(self):
        html = (
            "<html><head><title>Hello</title></head>"
            "<body><script>steal_creds()</script><p>Welcome friend</p></body></html>"
        )
        features = make_features("https://example.com", html)
        text = extract_semantic_text(features)
        assert "steal_creds" not in text
        assert "Welcome friend" in text

    def test_includes_form_input_tokens(self):
        html = (
            "<html><body>"
            "<form action='/login'><input type='password' name='passwd'></form>"
            "</body></html>"
        )
        features = make_features("https://example.com", html)
        text = extract_semantic_text(features)
        assert "input:password" in text
        assert "passwd" in text

    def test_redacts_in_extracted_text(self):
        html = "<html><body><p>Email: bob@example.com</p></body></html>"
        features = make_features("https://example.com", html)
        text = extract_semantic_text(features)
        assert "bob@example.com" not in text
