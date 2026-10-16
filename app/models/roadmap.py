"""Roadmaps, stages, learning resources, calendar events and registrations."""

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
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    RegistrationStatus,
    ResourceStatus,
    SkillLevel,
    StageStatus,
    TimestampMixin,
    UUIDMixin,
)


class Roadmap(Base, UUIDMixin, TimestampMixin):
    """A personalised three-stage development plan for a target role."""

    __tablename__ = "roadmaps"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_role: Mapped[str] = mapped_column(String(120), nullable=False)
    role_key: Mapped[str | None] = mapped_column(String(100))
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    total_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    gap_report: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # output of gap analysis
    prompt_version: Mapped[str | None] = mapped_column(String(40))

    stages: Mapped[list[Stage]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="Stage.order"
    )


class Stage(Base, UUIDMixin, TimestampMixin):
    """One of Beginner / Intermediate / Advanced within a roadmap."""

    __tablename__ = "stages"

    roadmap_id: Mapped[str] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, native_enum=False, length=20), nullable=False
    )
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)  # skill keys to acquire
    projects: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    milestones: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    weekly_plan: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    estimated_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_weeks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus, native_enum=False, length=20), default=StageStatus.LOCKED
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roadmap: Mapped[Roadmap] = relationship(back_populates="stages")
    resources: Mapped[list[Resource]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class Resource(Base, UUIDMixin, TimestampMixin):
    """A course / tutorial / workshop / event found by web search for a skill gap."""

    __tablename__ = "resources"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), index=True
    )
    skill_key: Mapped[str | None] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(30), default="course"
    )  # course/tutorial/workshop/event
    cost: Mapped[str | None] = mapped_column(String(60))  # "Free", "$49", ...
    is_free: Mapped[bool | None] = mapped_column(Boolean)
    duration: Mapped[str | None] = mapped_column(String(60))
    level: Mapped[SkillLevel | None] = mapped_column(Enum(SkillLevel, native_enum=False, length=20))
    rating: Mapped[float | None] = mapped_column(Float)
    event_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    why_chosen: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    url_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, native_enum=False, length=20), default=ResourceStatus.SUGGESTED
    )
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # original search hit

    stage: Mapped[Stage | None] = relationship(back_populates="resources")


class CalendarEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "calendar_events"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(20), default="google", nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reminders_minutes: Mapped[list[int]] = mapped_column(JSON, default=list)
    html_link: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned/created/failed


class Registration(Base, UUIDMixin, TimestampMixin):
    """An automated workshop registration (Playwright) gated by user confirmation."""

    __tablename__ = "registrations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    approval_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL")
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, native_enum=False, length=20), default=RegistrationStatus.PREVIEW
    )
    preview: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # what will be submitted
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
