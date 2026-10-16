"""Authentication routes.

Three surfaces share the same service layer:
- HTML pages + form posts (`/login`, `/register`, `/auth/*`) used by the web UI
- JSON API (`/api/v1/auth/*`) used by tests and any future mobile client
- OAuth redirects (`/auth/{provider}/login` -> provider -> `/auth/{provider}/callback`)

Tokens are set as httpOnly cookies; the browser never sees them from JS.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser, OptionalUser
from app.core.rate_limit import rate_limit
from app.core.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    create_token,
    decode_token,
)
from app.core.templating import is_htmx, templates
from app.integrations import oauth as oauth_mod
from app.models import User
from app.schemas.auth import LoginRequest, MessageOut, RegisterRequest, UserOut
from app.services import auth_service
from app.services.auth_service import AuthError

logger = logging.getLogger(__name__)

pages = APIRouter(tags=["auth-pages"])
api = APIRouter(prefix="/api/v1/auth", tags=["auth-api"])


# ---------- Cookie helpers ----------
def set_auth_cookies(response: Response, user: User) -> None:
    settings = get_settings()
    common = {"httponly": True, "samesite": "lax", "secure": settings.cookies_secure, "path": "/"}
    response.set_cookie(
        ACCESS_COOKIE,
        create_token(user.id, "access"),
        max_age=settings.access_token_minutes * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_token(user.id, "refresh"),
        max_age=settings.refresh_token_days * 86400,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _safe_next(next_path: str | None) -> str:
    """Only allow same-site relative redirects (prevents open redirects)."""
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/dashboard"


def _validation_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first.get("loc", ()))
    msg = first.get("msg", "Invalid input").removeprefix("Value error, ")
    return f"{field}: {msg}" if field else msg


# =====================================================================
# HTML pages
# =====================================================================
@pages.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: OptionalUser, next: str | None = None):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request, "auth/login.html", {"user": None, "next": _safe_next(next), "error": None}
    )


@pages.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: OptionalUser):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request, "auth/register.html", {"user": None, "error": None, "form": {}}
    )


@pages.post("/auth/register", dependencies=[Depends(rate_limit(10, 300))])
async def register_submit(
    request: Request,
    db: DB,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    full_name: Annotated[str, Form()],
    accept_terms: Annotated[bool, Form()] = False,
):
    form = {"email": email, "full_name": full_name}
    try:
        data = RegisterRequest(
            email=email, password=password, full_name=full_name, accept_terms=accept_terms
        )
        user = await auth_service.register_user(db, data, request)
    except ValidationError as exc:
        return _form_error(request, "auth/register.html", _validation_message(exc), form=form)
    except AuthError as exc:
        return _form_error(request, "auth/register.html", exc.message, form=form)

    response = _redirect_after_auth(request, "/dashboard")
    set_auth_cookies(response, user)
    return response


@pages.post("/auth/login", dependencies=[Depends(rate_limit(10, 60))])
async def login_submit(
    request: Request,
    db: DB,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str | None, Form()] = None,
):
    try:
        user = await auth_service.authenticate(
            db, LoginRequest(email=email, password=password), request
        )
    except ValidationError as exc:
        return _form_error(request, "auth/login.html", _validation_message(exc), next=next)
    except AuthError as exc:
        return _form_error(request, "auth/login.html", exc.message, next=next)

    response = _redirect_after_auth(request, _safe_next(next))
    set_auth_cookies(response, user)
    return response


@pages.post("/auth/logout")
async def logout_submit(request: Request):
    response = _redirect_after_auth(request, "/")
    clear_auth_cookies(response)
    return response


def _form_error(request: Request, template: str, message: str, **ctx):
    """Re-render the form with an error. HTMX gets just the form partial."""
    context = {"user": None, "error": message, "form": {}, "next": "/dashboard", **ctx}
    if is_htmx(request):
        partial = template.replace(".html", "_form.html")
        return templates.TemplateResponse(request, partial, context, status_code=422)
    return templates.TemplateResponse(request, template, context, status_code=422)


def _redirect_after_auth(request: Request, url: str) -> Response:
    if is_htmx(request):
        return Response(status_code=204, headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


# =====================================================================
# OAuth (LinkedIn OIDC, Google)
# =====================================================================
@pages.get("/auth/{provider}/login")
async def oauth_login(request: Request, provider: str, calendar: bool = False, gmail: bool = False):
    if not oauth_mod.provider_enabled(provider):
        raise HTTPException(status_code=404, detail=f"{provider} sign-in is not configured")
    client = getattr(oauth_mod.oauth, provider)
    redirect_uri = f"{get_settings().base_url}/auth/{provider}/callback"
    kwargs: dict = {}
    if provider == "google":
        kwargs["scope"] = oauth_mod.google_extra_scopes(calendar=calendar, gmail=gmail)
        kwargs["access_type"] = "offline"
        kwargs["include_granted_scopes"] = "true"
        if calendar or gmail:
            kwargs["prompt"] = "consent"  # ensures a refresh token for background jobs
    return await client.authorize_redirect(request, redirect_uri, **kwargs)


@pages.get("/auth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db: DB, user: OptionalUser):
    if not oauth_mod.provider_enabled(provider):
        raise HTTPException(status_code=404, detail=f"{provider} sign-in is not configured")
    client = getattr(oauth_mod.oauth, provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:  # Authlib raises many error types; treat all as a failed login
        logger.warning("OAuth callback failed for %s: %s", provider, exc)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"user": None, "next": "/dashboard", "error": f"{provider.title()} sign-in failed."},
            status_code=400,
        )
    identity = oauth_mod.extract_identity(provider, token)
    if not identity["provider_user_id"]:
        raise HTTPException(status_code=400, detail="Provider returned no user id")
    try:
        linked_user = await auth_service.upsert_oauth_account(
            db,
            provider=provider,
            provider_user_id=identity["provider_user_id"],
            email=identity["email"],
            display_name=identity["display_name"],
            picture_url=identity["picture_url"],
            token=dict(token),
            request=request,
            current_user=user,
        )
    except AuthError as exc:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"user": None, "next": "/dashboard", "error": exc.message},
            status_code=exc.status_code,
        )
    response = RedirectResponse("/settings" if user else "/dashboard", status_code=303)
    set_auth_cookies(response, linked_user)
    return response


# =====================================================================
# JSON API
# =====================================================================
@api.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(rate_limit(10, 300))],
)
async def api_register(request: Request, data: RegisterRequest, db: DB):
    try:
        user = await auth_service.register_user(db, data, request)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    response = JSONResponse(_user_out(user), status_code=201)
    set_auth_cookies(response, user)
    return response


@api.post("/login", response_model=UserOut, dependencies=[Depends(rate_limit(10, 60))])
async def api_login(request: Request, data: LoginRequest, db: DB):
    try:
        user = await auth_service.authenticate(db, data, request)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    response = JSONResponse(_user_out(user))
    set_auth_cookies(response, user)
    return response


@api.post("/logout", response_model=MessageOut)
async def api_logout():
    response = JSONResponse({"message": "Logged out"})
    clear_auth_cookies(response)
    return response


@api.post("/refresh", response_model=UserOut)
async def api_refresh(request: Request, db: DB):
    """Exchange a valid refresh cookie for a new access/refresh pair."""
    token = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(token, "refresh") if token else None
    user = await auth_service.get_user_by_id(db, payload["sub"]) if payload else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    response = JSONResponse(_user_out(user))
    set_auth_cookies(response, user)
    return response


@api.get("/me", response_model=UserOut)
async def api_me(user: CurrentUser):
    return _user_out(user)


def _user_out(user: User) -> dict:
    out = UserOut.model_validate(user)
    out.has_password = bool(user.password_hash)
    return out.model_dump(mode="json")
