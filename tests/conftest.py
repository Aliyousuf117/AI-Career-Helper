"""Shared pytest fixtures.

Environment variables are set *before* any `app` import so the cached settings
and the engine use an in-memory SQLite database.
"""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["LINKEDIN_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""

from collections.abc import AsyncIterator  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
async def _fresh_db() -> AsyncIterator[None]:
    """Recreate all tables for every test, and reset rate limits."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    reset_rate_limits()
    yield


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def register(
    client: httpx.AsyncClient, email: str = "sara@example.com", password: str = "s3cret-pass"
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Sara Ali", "accept_terms": True},
    )


@pytest.fixture
async def auth_client(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """A client that is already registered and logged in (cookies set)."""
    resp = await register(client)
    assert resp.status_code == 201, resp.text
    return client
