"""Session signing, OAuth-token encryption and webhook signature checks.

Three separate concerns share one secret (``SESSION_SECRET``) but never the
same key material: each key is derived through HKDF with a distinct info
label, so leaking one derived key does not compromise the others.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

SESSION_COOKIE_NAME = "dap_session"
OAUTH_STATE_COOKIE_NAME = "dap_oauth_state"
JWT_ALGORITHM = "HS256"


def _derive_key(info: str, length: int = 32) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=b"discord-automation-platform",
        info=info.encode(),
    ).derive(settings.session_secret.encode())


_fernet = Fernet(base64.urlsafe_b64encode(_derive_key("oauth-token-encryption")))
_jwt_key = _derive_key("session-jwt")


# --------------------------------------------------------------------------
# Session cookie (stateless JWT)
# --------------------------------------------------------------------------
def create_session_token(user_id: int, discord_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "did": discord_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.session_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, _jwt_key, algorithm=JWT_ALGORITHM)


def read_session_token(token: str) -> dict[str, Any] | None:
    """Return the payload, or ``None`` when the token is invalid or expired."""
    try:
        return jwt.decode(token, _jwt_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# --------------------------------------------------------------------------
# OAuth token storage
# --------------------------------------------------------------------------
def encrypt_token(raw: str | None) -> bytes | None:
    return _fernet.encrypt(raw.encode()) if raw else None


def decrypt_token(blob: bytes | None) -> str | None:
    if not blob:
        return None
    try:
        return _fernet.decrypt(blob).decode()
    except InvalidToken:  # secret rotated -- force a fresh login
        return None


# --------------------------------------------------------------------------
# CSRF protection for the OAuth round trip
# --------------------------------------------------------------------------
def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def verify_oauth_state(received: str | None, expected: str | None) -> bool:
    if not received or not expected:
        return False
    return hmac.compare_digest(received, expected)


# --------------------------------------------------------------------------
# Inbound webhooks
# --------------------------------------------------------------------------
def sign_payload(body: bytes, secret: str | None = None) -> str:
    """Return the ``sha256=<hex>`` signature expected in ``X-Signature``."""
    key = (secret or settings.webhook_secret).encode()
    digest = hmac.new(key, body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(body: bytes, header_value: str | None) -> bool:
    if not header_value:
        return False
    return hmac.compare_digest(sign_payload(body), header_value.strip())
