"""Request / response schemas for authentication."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    accept_terms: bool = False

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name is required")
        return v

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms and the AI guidance disclaimer")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None  # None allowed for OAuth-only users setting a password
    new_password: str = Field(min_length=8, max_length=128)


class OAuthAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    email: str | None
    display_name: str | None
    scopes: str
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    is_verified: bool
    has_password: bool = False
    created_at: datetime
    last_login_at: datetime | None = None


class MessageOut(BaseModel):
    message: str
