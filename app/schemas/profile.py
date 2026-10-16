"""Schemas for the profile and background entities."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.base import Budget, ExperienceKind, UserStatus


def _empty_to_none(v: object) -> object:
    """HTML forms send '' for blank fields; treat that as null."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


class ProfileUpdate(BaseModel):
    """All fields optional; only provided ones are applied."""

    status: UserStatus | None = None
    target_role: str | None = Field(default=None, max_length=120)
    target_field: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=220)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None
    education: str | None = Field(default=None, max_length=255)
    weekly_hours: int | None = Field(default=None, ge=1, le=80)
    goal_date: date | None = None
    budget: Budget | None = None
    preferred_language: str | None = Field(default=None, max_length=40)
    learning_style: str | None = Field(default=None, max_length=60)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        return _empty_to_none(v)

    @field_validator("linkedin_url")
    @classmethod
    def _linkedin_domain(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and "linkedin.com" not in (v.host or ""):
            raise ValueError("Must be a linkedin.com URL")
        return v


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: UserStatus | None
    target_role: str | None
    target_field: str | None
    headline: str | None
    bio: str | None
    location: str | None
    phone: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    education: str | None
    weekly_hours: int | None
    goal_date: date | None
    budget: Budget
    preferred_language: str
    learning_style: str | None
    onboarding_step: int
    completeness: int
    updated_at: datetime


class CertificateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=255)
    credential_url: HttpUrl | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        return _empty_to_none(v)


class CertificateOut(CertificateIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    verified: bool
    credential_url: str | None = None


class ExperienceIn(BaseModel):
    kind: ExperienceKind = ExperienceKind.WORK
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=3000)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        return _empty_to_none(v)


class ExperienceOut(ExperienceIn):
    model_config = ConfigDict(from_attributes=True)

    id: str


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=3000)
    url: HttpUrl | None = None
    technologies: list[str] = Field(default_factory=list)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        return _empty_to_none(v)

    @field_validator("technologies", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []


class ProjectOut(ProjectIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str | None = None
