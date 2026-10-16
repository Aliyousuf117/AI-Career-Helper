"""Symmetric encryption for secrets at rest (OAuth tokens).

Uses Fernet (AES-128-CBC + HMAC). The key comes from `TOKEN_ENCRYPTION_KEY`.
In development, if the key is missing we derive one from `SECRET_KEY` so the
app still runs; production must set a real key.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.token_encryption_key.strip()
    if not key:
        if settings.is_production:
            raise RuntimeError("TOKEN_ENCRYPTION_KEY must be set in production")
        # Deterministic dev key derived from SECRET_KEY (32 bytes, urlsafe-b64).
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt(plaintext: str | None) -> str | None:
    """Encrypt a string; returns None for None/empty input."""
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str | None) -> str | None:
    """Decrypt a string produced by `encrypt`. Returns None if invalid."""
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
