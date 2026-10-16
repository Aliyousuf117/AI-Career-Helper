"""Unit tests for password hashing, JWTs and token encryption."""

from __future__ import annotations

from datetime import timedelta

from app.core import crypto
from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("correct horse")
    assert h != "correct horse"
    assert verify_password("correct horse", h)
    assert not verify_password("wrong", h)
    assert not verify_password("anything", None)


def test_jwt_type_is_enforced():
    access = create_token("user-1", "access")
    assert decode_token(access, "access")["sub"] == "user-1"
    # An access token must not be accepted where a refresh token is expected.
    assert decode_token(access, "refresh") is None


def test_jwt_expired_and_tampered():
    expired = create_token("user-1", "access", expires_delta=timedelta(seconds=-5))
    assert decode_token(expired, "access") is None
    good = create_token("user-1", "access")
    assert decode_token(good[:-2] + "xx", "access") is None


def test_token_encryption_roundtrip():
    secret = "ya29.oauth-access-token"
    enc = crypto.encrypt(secret)
    assert enc and secret not in enc
    assert crypto.decrypt(enc) == secret
    assert crypto.encrypt(None) is None
    assert crypto.decrypt("not-a-valid-token") is None
