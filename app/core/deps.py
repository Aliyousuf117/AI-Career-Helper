"""FastAPI dependencies: database session and current-user resolution.

Two flavours of "who is logged in":
- `current_user_optional` -> User | None (used by public pages to show nav state)
- `current_user_required` -> User, or 401 for `/api/...` paths, or a redirect to
  `/login?next=...` for HTML pages.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import ACCESS_COOKIE, decode_token
from app.models import User
from app.services.auth_service import get_user_by_id

DB = Annotated[AsyncSession, Depends(get_db)]


class LoginRedirect(Exception):
    """Raised for HTML routes; converted to a 302 by the handler in `main.py`."""

    def __init__(self, next_path: str) -> None:
        self.next_path = next_path

    def response(self) -> RedirectResponse:
        return RedirectResponse(url=f"/login?next={self.next_path}", status_code=302)


async def current_user_optional(request: Request, db: DB) -> User | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    payload = decode_token(token, "access")
    if payload is None:
        return None
    user = await get_user_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        return None
    return user


async def current_user_required(
    request: Request, user: Annotated[User | None, Depends(current_user_optional)]
) -> User:
    if user is not None:
        return user
    if request.url.path.startswith("/api/"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # HTMX requests can't follow a 302 to a full page nicely; tell HTMX to redirect.
    if request.headers.get("HX-Request") == "true":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"HX-Redirect": "/login"},
        )
    raise LoginRedirect(request.url.path)


CurrentUser = Annotated[User, Depends(current_user_required)]
OptionalUser = Annotated[User | None, Depends(current_user_optional)]
