"""
Security service - HMAC signature validation.
"""
import base64, hashlib, hmac
from app.config import get_config


def get_secret() -> bytes:
    """
    Get the HMAC secret from environment variable.
    The secret is stored as base64-encoded string.
    
    Raises:
        ValueError: If POKEPROXY_SECRET is not set
    """
    secret_b64 = get_config().pokeproxy_secret
    if not secret_b64:
        raise ValueError("POKEPROXY_SECRET environment variable is not set")
    return base64.b64decode(secret_b64)


def validate_signature(body: bytes, signature: str, secret: bytes) -> bool:
    """
    Validate HMAC-SHA256 signature of the request body.
    Uses timing-safe comparison to prevent timing attacks.
    
    Returns False for malformed or invalid signatures instead of raising exceptions.
    """
    try:
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (ValueError, TypeError):
        # Malformed signature string
        return False
