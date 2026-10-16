"""FastAPI application factory and entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, health, me, pages
from app.core.config import get_settings
from app.core.database import create_all_tables
from app.core.deps import LoginRedirect
from app.core.logging import setup_logging
from app.core.templating import templates

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        await create_all_tables()
        logger.info("Database tables ensured (AUTO_CREATE_TABLES=true)")
    logger.info(
        "%s started (env=%s, model=%s)", settings.app_name, settings.app_env, settings.claude_model
    )
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI-powered career coach: learning chatbot + career agent.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Server-side session (signed cookie) is required by Authlib for the OAuth `state`.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="ach_session",
        https_only=settings.cookies_secure,
        same_site="lax",
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(health.router)
    app.include_router(auth.pages)
    app.include_router(auth.api)
    app.include_router(me.router)
    app.include_router(pages.router)

    # ---- Exception handling ----
    @app.exception_handler(LoginRedirect)
    async def _login_redirect(_: Request, exc: LoginRedirect):
        return exc.response()

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        wants_json = request.url.path.startswith("/api/") or "text/html" not in request.headers.get(
            "accept", ""
        )
        if wants_json:
            return JSONResponse(
                {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
            )
        return templates.TemplateResponse(
            request,
            "error.html",
            {"user": None, "status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # Drop `ctx`/`input`: they can hold exception objects (not JSON) or echo secrets.
        errors = [
            {k: v for k, v in err.items() if k not in ("ctx", "input", "url")}
            for err in exc.errors()
        ]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    return app


app = create_app()
