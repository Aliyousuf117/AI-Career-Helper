"""Integration tests for registration, login, logout, refresh, rate limiting."""

from __future__ import annotations

from sqlalchemy import select

from app.core.security import ACCESS_COOKIE, REFRESH_COOKIE
from app.models import AuditLog, User
from tests.conftest import register


async def test_register_sets_httponly_cookies(client):
    resp = await register(client)
    assert resp.status_code == 201
    assert resp.json()["email"] == "sara@example.com"
    set_cookie = resp.headers.get_list("set-cookie")
    assert any(c.startswith(f"{ACCESS_COOKIE}=") and "HttpOnly" in c for c in set_cookie)
    assert any(c.startswith(f"{REFRESH_COOKIE}=") and "HttpOnly" in c for c in set_cookie)


async def test_register_requires_terms(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@example.com",
            "password": "longenough",
            "full_name": "A",
            "accept_terms": False,
        },
    )
    assert resp.status_code == 422


async def test_register_duplicate_email(client):
    await register(client)
    resp = await register(client)
    assert resp.status_code == 409


async def test_login_logout_me(client, db):
    await register(client)
    await client.post("/api/v1/auth/logout")
    client.cookies.clear()
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    bad = await client.post(
        "/api/v1/auth/login", json={"email": "sara@example.com", "password": "nope"}
    )
    assert bad.status_code == 401

    ok = await client.post(
        "/api/v1/auth/login", json={"email": "SARA@example.com", "password": "s3cret-pass"}
    )
    assert ok.status_code == 200
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["has_password"] is True

    actions = [a.action for a in (await db.execute(select(AuditLog))).scalars()]
    assert {"auth.register", "auth.login_failed", "auth.login"} <= set(actions)


async def test_refresh_issues_new_tokens(auth_client):
    auth_client.cookies.delete(ACCESS_COOKIE)
    resp = await auth_client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 200


async def test_login_rate_limited(client):
    for _ in range(10):
        await client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "bad"})
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "x@example.com", "password": "bad"}
    )
    assert resp.status_code == 429


async def test_html_login_flow_and_protected_redirect(client):
    # Protected page redirects anonymous users to /login
    resp = await client.get("/dashboard", headers={"accept": "text/html"})
    assert resp.status_code == 302 and resp.headers["location"].startswith("/login")

    await register(client)
    client.cookies.clear()
    form = {"email": "sara@example.com", "password": "s3cret-pass", "next": "/profile"}
    resp = await client.post("/auth/login", data=form)
    assert resp.status_code == 303 and resp.headers["location"] == "/profile"

    page = await client.get("/dashboard")
    assert page.status_code == 200 and "Welcome, Sara Ali" in page.text


async def test_open_redirect_blocked(client):
    await register(client)
    client.cookies.clear()
    form = {"email": "sara@example.com", "password": "s3cret-pass", "next": "//evil.example.com"}
    resp = await client.post("/auth/login", data=form)
    assert resp.headers["location"] == "/dashboard"


async def test_password_stored_hashed(client, db):
    await register(client)
    user = (await db.execute(select(User))).scalar_one()
    assert user.password_hash and "s3cret-pass" not in user.password_hash
