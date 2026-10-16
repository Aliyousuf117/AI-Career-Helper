"""Profile and background: certificates, experience, projects."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    Budget,
    ExperienceKind,
    TimestampMixin,
    UserStatus,
    UUIDMixin,
)

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Base, UUIDMixin, TimestampMixin):
    """One profile per user: who they are, what they target, and learning constraints."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[UserStatus | None] = mapped_column(
        Enum(UserStatus, native_enum=False, length=20), nullable=True
    )
    target_role: Mapped[str | None] = mapped_column(String(120))  # e.g. "Python developer"
    target_field: Mapped[str | None] = mapped_column(String(120))  # e.g. "Software engineering"
    headline: Mapped[str | None] = mapped_column(String(220))
    bio: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    github_url: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(255))
    education: Mapped[str | None] = mapped_column(String(255))  # e.g. "BSc CS, 2025"

    # --- Learning constraints (chatbot step 3) ---
    weekly_hours: Mapped[int | None] = mapped_column(Integer)
    goal_date: Mapped[date | None] = mapped_column(Date)
    budget: Mapped[Budget] = mapped_column(
        Enum(Budget, native_enum=False, length=10), default=Budget.ANY, nullable=False
    )
    preferred_language: Mapped[str] = mapped_column(String(40), default="English", nullable=False)
    learning_style: Mapped[str | None] = mapped_column(String(60))  # video / reading / hands-on

    # --- Chatbot progress + summaries filled by later phases ---
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    user: Mapped[User] = relationship(back_populates="profile")

    @property
    def completeness(self) -> int:
        """Rough % of the profile filled in (shown on the dashboard)."""
        fields = [
            self.status,
            self.target_role,
            self.headline,
            self.location,
            self.weekly_hours,
            self.goal_date,
            self.learning_style,
            self.bio,
        ]
        filled = sum(1 for f in fields if f not in (None, ""))
        return round(100 * filled / len(fields))


class Certificate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "certificates"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(255))
    credential_url: Mapped[str | None] = mapped_column(String(500))
    skills: Mapped[list[str] | None] = mapped_column(JSON)  # skill keys covered
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="certificates")


class Experience(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "experiences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[ExperienceKind] = mapped_column(
        Enum(ExperienceKind, native_enum=False, length=20),
        default=ExperienceKind.WORK,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)  # null => current
    description: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str] | None] = mapped_column(JSON)

    user: Mapped[User] = relationship(back_populates="experiences")


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    technologies: Mapped[list[str] | None] = mapped_column(JSON)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # Set when the project was produced inside a roadmap stage (verified work).
    stage_id: Mapped[str | None] = mapped_column(ForeignKey("stages.id", ondelete="SET NULL"))

    user: Mapped[User] = relationship(back_populates="projects")
