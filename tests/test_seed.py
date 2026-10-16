"""The taxonomy seed is valid, idempotent and referentially consistent."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Role, RoleSkillRequirement, Skill
from scripts.seed import seed_demo_user, seed_taxonomy


async def test_seed_is_idempotent(db):
    n_skills, n_roles = await seed_taxonomy(db)
    await seed_taxonomy(db)  # second run must not duplicate
    assert (await db.execute(select(func.count()).select_from(Skill))).scalar_one() == n_skills
    assert (await db.execute(select(func.count()).select_from(Role))).scalar_one() == n_roles
    reqs = (await db.execute(select(func.count()).select_from(RoleSkillRequirement))).scalar_one()
    assert reqs > 0


async def test_python_developer_role_exists(db):
    await seed_taxonomy(db)
    role = (await db.execute(select(Role).where(Role.key == "python_developer"))).scalar_one()
    assert role.name == "Python Developer"


async def test_demo_user(db):
    assert await seed_demo_user(db) is True
    assert await seed_demo_user(db) is False
