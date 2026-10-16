"""Quizzes (level assessment + stage tests) and attempts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, QuizKind, TimestampMixin, UUIDMixin


class Quiz(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quizzes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stage_id: Mapped[str | None] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"))
    kind: Mapped[QuizKind] = mapped_column(
        Enum(QuizKind, native_enum=False, length=30), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # List of question dicts: {id, type: mcq|short|code, skill_key, difficulty, prompt, options,
    # answer, tests}. Answers are never sent to the client.
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    passing_score: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(40))

    attempts: Mapped[list[QuizAttempt]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class QuizAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # question_id -> answer
    per_question: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool | None] = mapped_column(Boolean)
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    skill_levels: Mapped[dict[str, str] | None] = mapped_column(JSON)  # skill_key -> level
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")
