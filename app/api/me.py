"""JSON API for the current user's account, profile and background."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.auth import clear_auth_cookies
from app.core.deps import DB, CurrentUser
from app.schemas.auth import ChangePasswordRequest, MessageOut, OAuthAccountOut
from app.schemas.profile import (
    CertificateIn,
    CertificateOut,
    ExperienceIn,
    ExperienceOut,
    ProfileOut,
    ProfileUpdate,
    ProjectIn,
    ProjectOut,
)
from app.services import auth_service, profile_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/v1/me", tags=["me"])


# ---------- Account ----------
@router.delete("", response_model=MessageOut)
async def delete_account(request: Request, user: CurrentUser, db: DB):
    """Delete the account and all associated data (GDPR-style erasure)."""
    await auth_service.delete_user_data(db, user, request)
    response = JSONResponse({"message": "Your account and all data have been deleted."})
    clear_auth_cookies(response)
    return response


@router.post("/password", response_model=MessageOut)
async def change_password(data: ChangePasswordRequest, user: CurrentUser, db: DB):
    try:
        await auth_service.change_password(db, user, data.current_password, data.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"message": "Password updated."}


@router.get("/oauth-accounts", response_model=list[OAuthAccountOut])
async def list_oauth_accounts(user: CurrentUser, db: DB):
    await db.refresh(user, ["oauth_accounts"])
    return user.oauth_accounts


@router.delete("/oauth-accounts/{provider}", response_model=MessageOut)
async def unlink_oauth(provider: str, user: CurrentUser, db: DB):
    try:
        removed = await auth_service.unlink_oauth_account(db, user, provider)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="No such linked account")
    return {"message": f"{provider} unlinked."}


# ---------- Profile ----------
@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: CurrentUser, db: DB):
    return await profile_service.get_or_create_profile(db, user)


@router.patch("/profile", response_model=ProfileOut)
async def patch_profile(data: ProfileUpdate, user: CurrentUser, db: DB):
    return await profile_service.update_profile(db, user, data)


# ---------- Certificates ----------
@router.get("/certificates", response_model=list[CertificateOut])
async def list_certificates(user: CurrentUser, db: DB):
    return await profile_service.list_certificates(db, user)


@router.post("/certificates", response_model=CertificateOut, status_code=201)
async def add_certificate(data: CertificateIn, user: CurrentUser, db: DB):
    return await profile_service.add_certificate(db, user, data)


@router.delete("/certificates/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(cert_id: str, user: CurrentUser, db: DB):
    if not await profile_service.delete_certificate(db, user, cert_id):
        raise HTTPException(status_code=404, detail="Certificate not found")


# ---------- Experience ----------
@router.get("/experiences", response_model=list[ExperienceOut])
async def list_experiences(user: CurrentUser, db: DB):
    return await profile_service.list_experiences(db, user)


@router.post("/experiences", response_model=ExperienceOut, status_code=201)
async def add_experience(data: ExperienceIn, user: CurrentUser, db: DB):
    return await profile_service.add_experience(db, user, data)


@router.delete("/experiences/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(exp_id: str, user: CurrentUser, db: DB):
    if not await profile_service.delete_experience(db, user, exp_id):
        raise HTTPException(status_code=404, detail="Experience not found")


# ---------- Projects ----------
@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(user: CurrentUser, db: DB):
    return await profile_service.list_projects(db, user)


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def add_project(data: ProjectIn, user: CurrentUser, db: DB):
    return await profile_service.add_project(db, user, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user: CurrentUser, db: DB):
    if not await profile_service.delete_project(db, user, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
