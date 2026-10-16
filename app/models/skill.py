"""Skill taxonomy, target roles and per-user skill levels."""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SkillLevel, SkillSource, TimestampMixin, UUIDMixin


class Skill(Base, UUIDMixin, TimestampMixin):
    """A node in the skill taxonomy, e.g. key="python.oop", category="Python"."""

    __tablename__ = "skills"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Comma-separated synonyms used to match CV text / job descriptions.
    aliases: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    requirements: Mapped[list[RoleSkillRequirement]] = relationship(back_populates="skill")

    @property
    def alias_list(self) -> list[str]:
        return [a.strip().lower() for a in self.aliases.split(",") if a.strip()]


class Role(Base, UUIDMixin, TimestampMixin):
    """A target career role, e.g. key="python_developer"."""

    __tablename__ = "roles"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    field: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[str] = mapped_column(Text, default="", nullable=False)

    requirements: Mapped[list[RoleSkillRequirement]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class RoleSkillRequirement(Base, UUIDMixin):
    """Minimum level of a skill required for a role (used by gap analysis)."""

    __tablename__ = "role_skill_requirements"
    __table_args__ = (UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),)

    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    min_level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, native_enum=False, length=20), nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # importance 0-1
    is_core: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped[Role] = relationship(back_populates="requirements")
    skill: Mapped[Skill] = relationship(back_populates="requirements")


class UserSkill(Base, UUIDMixin, TimestampMixin):
    """The user's current level in a skill, with where that evidence came from."""

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, native_enum=False, length=20), default=SkillLevel.NONE, nullable=False
    )
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, native_enum=False, length=20),
        default=SkillSource.SELF_REPORTED,
        nullable=False,
    )
    evidence: Mapped[str | None] = mapped_column(Text)  # e.g. "Built REST API at ACME"
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0-1
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    skill: Mapped[Skill] = relationship()
