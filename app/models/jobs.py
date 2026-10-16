"""Job postings from legal providers and the user's matches / application tracker."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JobMatchStatus, TimestampMixin, UUIDMixin


class JobPosting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_job_provider_ext"),)

    provider: Mapped[str] = mapped_column(String(40), nullable=False)  # adzuna/jsearch/remotive...
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    is_remote: Mapped[bool | None] = mapped_column(Boolean)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    apply_url: Mapped[str | None] = mapped_column(String(1000))
    apply_email: Mapped[str | None] = mapped_column(String(255))  # contact from job data only
    contact_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str] | None] = mapped_column(JSON)  # extracted skill keys
    salary: Mapped[str | None] = mapped_column(String(120))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    matches: Mapped[list[JobMatch]] = relationship(back_populates="job")


class JobMatch(Base, UUIDMixin, TimestampMixin):
    """Scored fit between a user and a posting; doubles as the application tracker row."""

    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    matched_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str | None] = mapped_column(Text)
    linkedin_search_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[JobMatchStatus] = mapped_column(
        Enum(JobMatchStatus, native_enum=False, length=20), default=JobMatchStatus.SUGGESTED
    )
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[JobPosting] = relationship(back_populates="matches")
