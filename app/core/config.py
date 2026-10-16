"""Application settings, loaded from environment variables / `.env`.

All secrets come from the environment. Nothing is hard-coded. Use
`get_settings()` everywhere (cached) rather than instantiating `Settings`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AI Career Helper"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    base_url: str = "http://localhost:8000"
    secret_key: str = Field(default="dev-only-insecure-secret-change-me", min_length=16)
    token_encryption_key: str = ""  # Fernet key; derived from SECRET_KEY in dev if empty
    auto_create_tables: bool = True

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"

    # --- Auth ---
    access_token_minutes: int = 60
    refresh_token_days: int = 14
    cookie_secure: bool | None = None  # None => secure only when app_env == production

    # --- Claude ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"

    # --- OAuth providers ---
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- Search / jobs (later phases) ---
    search_provider: str = "tavily"
    tavily_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    rapidapi_key: str = ""

    # --- Uploads ---
    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_mb: int = 10

    @field_validator("upload_dir", mode="before")
    @classmethod
    def _abs_upload_dir(cls, v: str | Path) -> Path:
        p = Path(v)
        return p if p.is_absolute() else PROJECT_ROOT / p

    # --- Derived helpers ---
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cookies_secure(self) -> bool:
        return self.is_production if self.cookie_secure is None else self.cookie_secure

    @property
    def linkedin_enabled(self) -> bool:
        return bool(self.linkedin_client_id and self.linkedin_client_secret)

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
