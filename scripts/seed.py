"""Seed the skill taxonomy (and optionally a demo user).

Idempotent: running it again updates existing skills/roles instead of duplicating.

    python -m scripts.seed            # taxonomy only
    python -m scripts.seed --demo     # + demo@example.com / demo12345
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT
from app.core.database import SessionLocal, create_all_tables
from app.core.security import hash_password
from app.models import (
    Budget,
    Profile,
    Role,
    RoleSkillRequirement,
    Skill,
    SkillLevel,
    User,
    UserStatus,
)

TAXONOMY_PATH = PROJECT_ROOT / "data" / "taxonomy.json"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"


async def seed_taxonomy(db: AsyncSession, path: Path = TAXONOMY_PATH) -> tuple[int, int]:
    """Upsert skills, roles and role requirements. Returns (n_skills, n_roles)."""
    data = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))

    existing = {s.key: s for s in (await db.execute(select(Skill))).scalars()}
    for order, item in enumerate(data["skills"]):
        skill = existing.get(item["key"]) or Skill(key=item["key"])
        skill.name = item["name"]
        skill.category = item["category"]
        skill.aliases = item.get("aliases", "")
        skill.description = item.get("description")
        skill.sort_order = order
        db.add(skill)
        existing[skill.key] = skill
    await db.flush()

    roles = {r.key: r for r in (await db.execute(select(Role))).scalars()}
    for item in data["roles"]:
        role = roles.get(item["key"]) or Role(key=item["key"])
        role.name = item["name"]
        role.field = item["field"]
        role.aliases = item.get("aliases", "")
        role.description = item.get("description")
        db.add(role)
        await db.flush()

        # Replace requirements wholesale so removals in the JSON are honoured.
        old = await db.execute(
            select(RoleSkillRequirement).where(RoleSkillRequirement.role_id == role.id)
        )
        for req in old.scalars():
            await db.delete(req)
        await db.flush()
        for req in item["requirements"]:
            if req["skill"] not in existing:
                raise ValueError(f"Role {role.key} references unknown skill {req['skill']}")
            db.add(
                RoleSkillRequirement(
                    role_id=role.id,
                    skill_id=existing[req["skill"]].id,
                    min_level=SkillLevel(req["min_level"]),
                    weight=req.get("weight", 1.0),
                    is_core=req.get("is_core", True),
                )
            )
    await db.commit()
    return len(data["skills"]), len(data["roles"])


async def seed_demo_user(db: AsyncSession) -> bool:
    """Create a demo job seeker targeting Python developer. Returns False if it exists."""
    found = await db.execute(select(User).where(User.email == DEMO_EMAIL))
    if found.scalar_one_or_none():
        return False
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Demo User",
        is_verified=True,
    )
    user.profile = Profile(
        status=UserStatus.JOB_SEEKER,
        target_role="Python developer",
        target_field="Software engineering",
        headline="IT graduate moving into Python development",
        location="Muscat, Oman",
        weekly_hours=6,
        budget=Budget.FREE,
        learning_style="Hands-on projects",
    )
    db.add(user)
    await db.commit()
    return True


async def main(demo: bool) -> None:
    await create_all_tables()
    async with SessionLocal() as db:
        n_skills, n_roles = await seed_taxonomy(db)
        print(f"Seeded {n_skills} skills and {n_roles} roles from {TAXONOMY_PATH.name}")
        if demo:
            created = await seed_demo_user(db)
            print(
                f"Demo user {'created' if created else 'already exists'}: "
                f"{DEMO_EMAIL} / {DEMO_PASSWORD}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="also create a demo user")
    asyncio.run(main(parser.parse_args().demo))
