"""HTML pages: landing, dashboard, profile, settings (Jinja2 + HTMX)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.api.auth import clear_auth_cookies
from app.core.deps import DB, CurrentUser, OptionalUser
from app.core.templating import is_htmx, templates
from app.integrations import oauth as oauth_mod
from app.models import Budget, ExperienceKind, UserStatus
from app.schemas.profile import CertificateIn, ExperienceIn, ProfileUpdate, ProjectIn
from app.services import auth_service, profile_service
from app.services.auth_service import AuthError

router = APIRouter(tags=["pages"])


def _errors(exc: ValidationError) -> list[str]:
    out = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", ())) or "form"
        out.append(f"{field}: {err.get('msg', 'invalid').removeprefix('Value error, ')}")
    return out


# ---------- Public ----------
@router.get("/", response_class=HTMLResponse)
async def landing(request: Request, user: OptionalUser):
    return templates.TemplateResponse(request, "index.html", {"user": user})


# ---------- Dashboard ----------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: CurrentUser, db: DB):
    profile = await profile_service.get_or_create_profile(db, user)
    certs = await profile_service.list_certificates(db, user)
    exps = await profile_service.list_experiences(db, user)
    projects = await profile_service.list_projects(db, user)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "profile": profile,
            "counts": {
                "certificates": len(certs),
                "experiences": len(exps),
                "projects": len(projects),
            },
        },
    )


# ---------- Profile ----------
async def _profile_context(request: Request, user, db) -> dict:
    return {
        "user": user,
        "profile": await profile_service.get_or_create_profile(db, user),
        "certificates": await profile_service.list_certificates(db, user),
        "experiences": await profile_service.list_experiences(db, user),
        "projects": await profile_service.list_projects(db, user),
        "statuses": list(UserStatus),
        "budgets": list(Budget),
        "experience_kinds": list(ExperienceKind),
    }


@router.get("/profile", response_class=HTMLResponse)
async def profile_view(request: Request, user: CurrentUser, db: DB):
    ctx = await _profile_context(request, user, db)
    return templates.TemplateResponse(request, "profile/view.html", ctx)


@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_edit(request: Request, user: CurrentUser, db: DB):
    ctx = await _profile_context(request, user, db)
    ctx["errors"] = []
    return templates.TemplateResponse(request, "profile/edit.html", ctx)


@router.post("/profile/edit", response_class=HTMLResponse)
async def profile_edit_submit(request: Request, user: CurrentUser, db: DB):
    form = dict(await request.form())
    try:
        data = ProfileUpdate(**form)
    except ValidationError as exc:
        ctx = await _profile_context(request, user, db)
        ctx["errors"] = _errors(exc)
        ctx["form"] = form
        template = "profile/_edit_form.html" if is_htmx(request) else "profile/edit.html"
        return templates.TemplateResponse(request, template, ctx, status_code=422)
    await profile_service.update_profile(db, user, data)
    if is_htmx(request):
        return Response(status_code=204, headers={"HX-Redirect": "/profile"})
    return RedirectResponse("/profile", status_code=303)


# ----- Background items: each POST/DELETE returns the refreshed list partial -----
@router.post("/profile/certificates", response_class=HTMLResponse)
async def add_certificate(request: Request, user: CurrentUser, db: DB):
    form = dict(await request.form())
    errors: list[str] = []
    try:
        await profile_service.add_certificate(db, user, CertificateIn(**form))
    except ValidationError as exc:
        errors = _errors(exc)
    return await _list_partial(request, user, db, "certificates", errors)


@router.delete("/profile/certificates/{cert_id}", response_class=HTMLResponse)
async def remove_certificate(cert_id: str, request: Request, user: CurrentUser, db: DB):
    await profile_service.delete_certificate(db, user, cert_id)
    return await _list_partial(request, user, db, "certificates")


@router.post("/profile/experiences", response_class=HTMLResponse)
async def add_experience(request: Request, user: CurrentUser, db: DB):
    form = dict(await request.form())
    errors: list[str] = []
    try:
        await profile_service.add_experience(db, user, ExperienceIn(**form))
    except ValidationError as exc:
        errors = _errors(exc)
    return await _list_partial(request, user, db, "experiences", errors)


@router.delete("/profile/experiences/{exp_id}", response_class=HTMLResponse)
async def remove_experience(exp_id: str, request: Request, user: CurrentUser, db: DB):
    await profile_service.delete_experience(db, user, exp_id)
    return await _list_partial(request, user, db, "experiences")


@router.post("/profile/projects", response_class=HTMLResponse)
async def add_project(request: Request, user: CurrentUser, db: DB):
    form = dict(await request.form())
    errors: list[str] = []
    try:
        await profile_service.add_project(db, user, ProjectIn(**form))
    except ValidationError as exc:
        errors = _errors(exc)
    return await _list_partial(request, user, db, "projects", errors)


@router.delete("/profile/projects/{project_id}", response_class=HTMLResponse)
async def remove_project(project_id: str, request: Request, user: CurrentUser, db: DB):
    await profile_service.delete_project(db, user, project_id)
    return await _list_partial(request, user, db, "projects")


async def _list_partial(request, user, db, kind: str, errors: list[str] | None = None):
    ctx = await _profile_context(request, user, db)
    ctx["errors"] = errors or []
    status = 422 if errors else 200
    if is_htmx(request):
        return templates.TemplateResponse(request, f"profile/_{kind}.html", ctx, status_code=status)
    return RedirectResponse("/profile", status_code=303)


# ---------- Settings ----------
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: CurrentUser, db: DB):
    await db.refresh(user, ["oauth_accounts"])
    return templates.TemplateResponse(
        request,
        "settings/index.html",
        {
            "user": user,
            "linked": {a.provider: a for a in user.oauth_accounts},
            "providers": {p: oauth_mod.provider_enabled(p) for p in oauth_mod.SUPPORTED_PROVIDERS},
            "message": None,
            "error": None,
        },
    )


@router.post("/settings/password", response_class=HTMLResponse)
async def settings_password(
    request: Request,
    user: CurrentUser,
    db: DB,
    new_password: Annotated[str, Form()],
    current_password: Annotated[str | None, Form()] = None,
):
    message = error = None
    if len(new_password) < 8:
        error = "New password must be at least 8 characters."
    else:
        try:
            await auth_service.change_password(db, user, current_password, new_password)
            message = "Password updated."
        except AuthError as exc:
            error = exc.message
    return templates.TemplateResponse(
        request,
        "settings/_password_form.html",
        {"user": user, "message": message, "error": error},
        status_code=200 if message else 400,
    )


@router.delete("/settings/oauth/{provider}", response_class=HTMLResponse)
async def settings_unlink(provider: str, request: Request, user: CurrentUser, db: DB):
    try:
        await auth_service.unlink_oauth_account(db, user, provider)
        error = None
    except AuthError as exc:
        error = exc.message
    await db.refresh(user, ["oauth_accounts"])
    return templates.TemplateResponse(
        request,
        "settings/_connected.html",
        {
            "user": user,
            "linked": {a.provider: a for a in user.oauth_accounts},
            "providers": {p: oauth_mod.provider_enabled(p) for p in oauth_mod.SUPPORTED_PROVIDERS},
            "error": error,
        },
    )


@router.delete("/settings/account")
async def settings_delete_account(request: Request, user: CurrentUser, db: DB):
    await auth_service.delete_user_data(db, user, request)
    response = Response(status_code=204, headers={"HX-Redirect": "/?deleted=1"})
    clear_auth_cookies(response)
    return response
