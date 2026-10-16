"""Career-agent records: approval queue, outreach messages, opt-outs and the audit log."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ApprovalStatus, Base, OutreachStatus, TimestampMixin, UUIDMixin, utcnow


class ApprovalRequest(Base, UUIDMixin, TimestampMixin):
    """Every action that changes something outside the app goes through here first."""

    __tablename__ = "approval_requests"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # e.g. "calendar.create_event", "registration.submit", "gmail.send", "profile.apply"
    action_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    preview: Mapped[str | None] = mapped_column(Text)  # human-readable description of the action
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # exact data to be used
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=20), default=ApprovalStatus.PENDING
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class OutreachMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "outreach_messages"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("job_postings.id", ondelete="SET NULL"))
    approval_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL")
    )
    channel: Mapped[str] = mapped_column(String(20), default="gmail")  # gmail | manual
    to_email: Mapped[str | None] = mapped_column(String(255), index=True)
    to_name: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attach_cv: Mapped[bool] = mapped_column(default=True)
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus, native_enum=False, length=20), default=OutreachStatus.DRAFTED
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    follow_up_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("outreach_messages.id", ondelete="SET NULL")
    )
    error: Mapped[str | None] = mapped_column(Text)


class OptOutContact(Base, UUIDMixin):
    """Stop-list: contacts that must never be messaged again."""

    __tablename__ = "opt_out_contacts"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_optout_user_email"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base, UUIDMixin):
    """Append-only record of security-relevant and external actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
