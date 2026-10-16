"""Liveness / readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import DB

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health(db: DB) -> dict:
    settings = get_settings()
    await db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "claude_model": settings.claude_model,
        "claude_configured": bool(settings.anthropic_api_key),
        "linkedin_oauth": settings.linkedin_enabled,
        "google_oauth": settings.google_enabled,
    }
