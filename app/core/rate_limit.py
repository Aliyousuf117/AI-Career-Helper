"""Tiny in-memory sliding-window rate limiter used as a FastAPI dependency.

Good enough for a single-process deployment (the graduation demo). Swap the
`_store` for Redis if the app is ever scaled horizontally.

Usage:
    @router.post("/login", dependencies=[Depends(rate_limit(10, 60))])
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

_store: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Create a dependency allowing `limit` requests per `window_seconds` per IP+path."""

    def dependency(request: Request) -> None:
        key = f"{client_ip(request)}:{request.url.path}"
        now = time.monotonic()
        bucket = _store[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
            )
        bucket.append(now)

    return dependency


def reset_rate_limits() -> None:
    """Clear all buckets (used by tests)."""
    _store.clear()
