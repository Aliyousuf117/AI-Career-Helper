"""Profile and background CRUD (certificates, experience, projects)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Certificate, Experience, Profile, Project, User
from app.schemas.profile import CertificateIn, ExperienceIn, ProfileUpdate, ProjectIn
from app.services.audit import log_action


async def get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_profile(db: AsyncSession, user: User, data: ProfileUpdate) -> Profile:
    """Apply only the fields that were explicitly provided."""
    profile = await get_or_create_profile(db, user)
    changes = data.model_dump(exclude_unset=True)
    # These columns are NOT NULL; a blank form field means "leave unchanged".
    for required in ("budget", "preferred_language"):
        if changes.get(required, ...) is None:
            changes.pop(required)
    for field, value in changes.items():
        # Pydantic HttpUrl -> str for storage
        setattr(profile, field, str(value) if value is not None and "url" in field else value)
    await log_action(
        db,
        "profile.updated",
        user_id=user.id,
        entity_type="profile",
        entity_id=profile.id,
        details={"fields": sorted(changes.keys())},
    )
    await db.commit()
    await db.refresh(profile)
    return profile


# ---------- Certificates ----------
async def list_certificates(db: AsyncSession, user: User) -> list[Certificate]:
    result = await db.execute(
        select(Certificate)
        .where(Certificate.user_id == user.id)
        .order_by(Certificate.issue_date.desc().nullslast(), Certificate.created_at.desc())
    )
    return list(result.scalars())


async def add_certificate(db: AsyncSession, user: User, data: CertificateIn) -> Certificate:
    cert = Certificate(user_id=user.id, **_dump(data))
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def delete_certificate(db: AsyncSession, user: User, cert_id: str) -> bool:
    return await _delete_owned(db, Certificate, user, cert_id)


# ---------- Experience ----------
async def list_experiences(db: AsyncSession, user: User) -> list[Experience]:
    result = await db.execute(
        select(Experience)
        .where(Experience.user_id == user.id)
        .order_by(Experience.start_date.desc().nullslast(), Experience.created_at.desc())
    )
    return list(result.scalars())


async def add_experience(db: AsyncSession, user: User, data: ExperienceIn) -> Experience:
    exp = Experience(user_id=user.id, **_dump(data))
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


async def delete_experience(db: AsyncSession, user: User, exp_id: str) -> bool:
    return await _delete_owned(db, Experience, user, exp_id)


# ---------- Projects ----------
async def list_projects(db: AsyncSession, user: User) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
    )
    return list(result.scalars())


async def add_project(db: AsyncSession, user: User, data: ProjectIn) -> Project:
    proj = Project(user_id=user.id, **_dump(data))
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj


async def delete_project(db: AsyncSession, user: User, project_id: str) -> bool:
    return await _delete_owned(db, Project, user, project_id)


# ---------- helpers ----------
def _dump(data: CertificateIn | ExperienceIn | ProjectIn) -> dict:
    out = data.model_dump()
    for key, value in list(out.items()):
        if value is not None and key.endswith("url"):
            out[key] = str(value)
    return out


async def _delete_owned(db: AsyncSession, model: type, user: User, obj_id: str) -> bool:
    result = await db.execute(select(model).where(model.id == obj_id, model.user_id == user.id))
    obj = result.scalar_one_or_none()
    if obj is None:
        return False
    await db.delete(obj)
    await db.commit()
    return True
