"""Claude client factory.

Phase 1 only wires configuration. Phase 2 adds the chatbot (streaming via SSE,
structured outputs validated with Pydantic, tool use). Keep every Claude call
going through `get_client()` so model/key handling lives in one place.
"""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic

from app.core.config import get_settings


@lru_cache
def get_client() -> AsyncAnthropic:
    """Return a shared async Anthropic client (reads ANTHROPIC_API_KEY from settings/env)."""
    settings = get_settings()
    kwargs: dict = {"max_retries": 3}
    if settings.anthropic_api_key:
        kwargs["api_key"] = settings.anthropic_api_key
    return AsyncAnthropic(**kwargs)


def model_name() -> str:
    """The model id from the `CLAUDE_MODEL` env var (default: claude-opus-5-5)."""
    return get_settings().claude_model


def llm_configured() -> bool:
    return bool(get_settings().anthropic_api_key)
