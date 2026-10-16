"""OAuth 2.0 / OpenID Connect clients (LinkedIn, Google) via Authlib.

Providers are registered only when their credentials exist in settings, so the
app runs fine without them (the sign-in buttons render as "not configured").

Google scopes are *incremental*: sign-in asks only for identity. Calendar and
Gmail scopes are requested later (Phases 5 and 9) through `google_extra_scopes`.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

LINKEDIN_METADATA = "https://www.linkedin.com/oauth/.well-known/openid-configuration"
GOOGLE_METADATA = "https://accounts.google.com/.well-known/openid-configuration"

GOOGLE_BASE_SCOPES = "openid email profile"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GOOGLE_GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

oauth = OAuth()
_settings = get_settings()

if _settings.linkedin_enabled:
    oauth.register(
        name="linkedin",
        client_id=_settings.linkedin_client_id,
        client_secret=_settings.linkedin_client_secret,
        server_metadata_url=LINKEDIN_METADATA,
        client_kwargs={
            "scope": "openid profile email",
            # LinkedIn expects client credentials in the POST body, not Basic auth.
            "token_endpoint_auth_method": "client_secret_post",
        },
    )

if _settings.google_enabled:
    oauth.register(
        name="google",
        client_id=_settings.google_client_id,
        client_secret=_settings.google_client_secret,
        server_metadata_url=GOOGLE_METADATA,
        client_kwargs={"scope": GOOGLE_BASE_SCOPES},
    )

SUPPORTED_PROVIDERS = ("linkedin", "google")


def provider_enabled(name: str) -> bool:
    return name in SUPPORTED_PROVIDERS and getattr(oauth, name, None) is not None


def google_extra_scopes(calendar: bool = False, gmail: bool = False) -> str:
    """Build the scope string for an incremental Google authorisation."""
    scopes = [GOOGLE_BASE_SCOPES]
    if calendar:
        scopes.append(GOOGLE_CALENDAR_SCOPE)
    if gmail:
        scopes.append(GOOGLE_GMAIL_SEND_SCOPE)
    return " ".join(scopes)


def extract_identity(provider: str, token: dict) -> dict[str, str | None]:
    """Normalise the OIDC `userinfo` claims into a provider-agnostic dict."""
    info = token.get("userinfo") or {}
    name = info.get("name") or " ".join(
        p for p in (info.get("given_name"), info.get("family_name")) if p
    )
    return {
        "provider_user_id": str(info.get("sub") or ""),
        "email": (info.get("email") or "").lower() or None,
        "display_name": name or None,
        "picture_url": info.get("picture"),
    }
