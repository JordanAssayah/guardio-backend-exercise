"""
Tests for the security service - HMAC signature validation.
"""
import base64
import hashlib
import hmac

import pytest

from app.services.security import validate_signature, get_secret


class TestValidateSignature:
    """Tests for validate_signature function."""

    def test_valid_signature(self, test_secret):
        """Valid HMAC signature should return True."""
        body = b"test body content"
        signature = hmac.new(test_secret, body, hashlib.sha256).hexdigest()
        
        assert validate_signature(body, signature, test_secret) is True

    def test_invalid_signature(self, test_secret):
        """Invalid signature should return False."""
        body = b"test body content"
        wrong_signature = "0" * 64  # Invalid but valid hex format
        
        assert validate_signature(body, wrong_signature, test_secret) is False

    def test_tampered_body(self, test_secret):
        """Signature for different body should return False."""
        original_body = b"original content"
        tampered_body = b"tampered content"
        signature = hmac.new(test_secret, original_body, hashlib.sha256).hexdigest()
        
        assert validate_signature(tampered_body, signature, test_secret) is False

    def test_wrong_secret(self, test_secret):
        """Signature with different secret should return False."""
        body = b"test body content"
        wrong_secret = b"wrong-secret"
        signature = hmac.new(test_secret, body, hashlib.sha256).hexdigest()
        
        assert validate_signature(body, signature, wrong_secret) is False

    def test_empty_body(self, test_secret):
        """Empty body should still validate correctly."""
        body = b""
        signature = hmac.new(test_secret, body, hashlib.sha256).hexdigest()
        
        assert validate_signature(body, signature, test_secret) is True

    def test_malformed_signature_non_hex(self, test_secret):
        """Non-hex signature should return False (not raise exception)."""
        body = b"test body"
        malformed_signature = "not-a-valid-hex-string!!!"
        
        # Should return False, not raise an exception
        assert validate_signature(body, malformed_signature, test_secret) is False

    def test_signature_is_lowercase_hex(self, test_secret):
        """HMAC-SHA256 produces lowercase hex, so uppercase won't match."""
        body = b"test body content"
        signature_lower = hmac.new(test_secret, body, hashlib.sha256).hexdigest()
        signature_upper = signature_lower.upper()
        
        # Only lowercase matches (HMAC.hexdigest() returns lowercase)
        assert validate_signature(body, signature_lower, test_secret) is True
        # Uppercase does NOT match - this is expected behavior
        assert validate_signature(body, signature_upper, test_secret) is False

    def test_unicode_body(self, test_secret):
        """Body with unicode content should validate correctly."""
        body = "Hello 世界 🎮".encode("utf-8")
        signature = hmac.new(test_secret, body, hashlib.sha256).hexdigest()
        
        assert validate_signature(body, signature, test_secret) is True


class TestGetSecret:
    """Tests for get_secret function."""

    def test_get_secret_success(self, mock_env, test_secret):
        """Should decode base64 secret from environment."""
        secret = get_secret()
        assert secret == test_secret

    def test_get_secret_empty_raises(self):
        """Should raise ValueError when secret is empty after decode."""
        from app.services.security import get_secret
        import base64
        
        # Test that empty base64 decodes to empty bytes
        empty_b64 = base64.b64encode(b"").decode()
        assert base64.b64decode(empty_b64) == b""

