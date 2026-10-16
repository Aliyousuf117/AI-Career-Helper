"""Jinja2 template environment shared by all page routers."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["settings"] = get_settings()


def is_htmx(request: Request) -> bool:
    """True when the request was issued by HTMX (so we can return partials)."""
    return request.headers.get("HX-Request") == "true"
