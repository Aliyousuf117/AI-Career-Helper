"""Declarative base, shared mixins and enumerations for all models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class UUIDMixin:
    """String UUID primary key (portable across SQLite and PostgreSQL)."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


# ---------- Enumerations (stored as short strings, not native DB enums) ----------
class UserStatus(enum.StrEnum):
    STUDENT = "student"
    JOB_SEEKER = "job_seeker"


class SkillLevel(enum.StrEnum):
    NONE = "none"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    @property
    def rank(self) -> int:
        """Numeric order used by gap analysis (none=0 ... advanced=3)."""
        return list(SkillLevel).index(self)


class Budget(enum.StrEnum):
    FREE = "free"
    PAID = "paid"
    ANY = "any"


class SkillSource(enum.StrEnum):
    SELF_REPORTED = "self_reported"
    CV = "cv"
    ASSESSMENT = "assessment"
    QUIZ = "quiz"
    CERTIFICATE = "certificate"


class DocumentKind(enum.StrEnum):
    CV = "cv"
    CERTIFICATE = "certificate"
    OTHER = "other"


class ExtractionStatus(enum.StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class ExperienceKind(enum.StrEnum):
    WORK = "work"
    INTERNSHIP = "internship"
    VOLUNTEER = "volunteer"
    FREELANCE = "freelance"


class StageStatus(enum.StrEnum):
    LOCKED = "locked"
    ACTIVE = "active"
    COMPLETED = "completed"


class ResourceStatus(enum.StrEnum):
    SUGGESTED = "suggested"
    SELECTED = "selected"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class RegistrationStatus(enum.StrEnum):
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    SUBMITTED = "submitted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuizKind(enum.StrEnum):
    LEVEL_ASSESSMENT = "level_assessment"
    STAGE_TEST = "stage_test"


class JobMatchStatus(enum.StrEnum):
    SUGGESTED = "suggested"
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class ApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class OutreachStatus(enum.StrEnum):
    DRAFTED = "drafted"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    FAILED = "failed"
