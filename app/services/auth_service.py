"""Authentication business logic shared by the JSON API and the HTML pages."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import crypto
from app.core.security import hash_password, verify_password
from app.models import OAuthAccount, Profile, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit import log_action

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised for user-facing authentication failures (safe to display)."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, data: RegisterRequest, request: Request | None) -> User:
    """Create a user + empty profile. Raises AuthError if the email is taken."""
    email = data.email.lower().strip()
    if await get_user_by_email(db, email):
        raise AuthError("An account with this email already exists.", 409)

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        consent_accepted_at=datetime.now(UTC),
    )
    user.profile = Profile()
    db.add(user)
    await db.flush()  # populate user.id for the audit row
    await log_action(db, "auth.register", user_id=user.id, request=request)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, data: LoginRequest, request: Request | None) -> User:
    """Verify email/password. Raises AuthError with a generic message on failure."""
    user = await get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        await log_action(
            db, "auth.login_failed", details={"email": data.email.lower()}, request=request
        )
        await db.commit()
        raise AuthError("Invalid email or password.", 401)
    if not user.is_active:
        raise AuthError("This account is disabled.", 403)

    user.last_login_at = datetime.now(UTC)
    await log_action(db, "auth.login", user_id=user.id, request=request)
    await db.commit()
    return user


async def change_password(
    db: AsyncSession, user: User, current_password: str | None, new_password: str
) -> None:
    if user.password_hash and not verify_password(current_password or "", user.password_hash):
        raise AuthError("Current password is incorrect.", 400)
    user.password_hash = hash_password(new_password)
    await log_action(db, "auth.password_changed", user_id=user.id)
    await db.commit()


async def upsert_oauth_account(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    email: str | None,
    display_name: str | None,
    picture_url: str | None,
    token: dict,
    request: Request | None,
    current_user: User | None = None,
) -> User:
    """Link an OAuth identity to the current user, or find/create a user for it.

    Resolution order:
    1. An existing OAuthAccount for (provider, provider_user_id) -> that user.
    2. The logged-in user (linking a provider from Settings).
    3. A user with the same verified email -> link.
    4. Otherwise create a new user without a password.
    Tokens are stored encrypted.
    """
    result = await db.execute(
        select(OAuthAccount)
        .options(selectinload(OAuthAccount.user))
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    account = result.scalar_one_or_none()

    if account is not None:
        user = account.user
    elif current_user is not None:
        user = current_user
    else:
        user = await get_user_by_email(db, email) if email else None
        if user is None:
            if not email:
                raise AuthError(
                    f"{provider.title()} did not share an email address; "
                    "please register with email first and link the account from Settings.",
                    400,
                )
            user = User(
                email=email.lower(),
                password_hash=None,
                full_name=display_name or email.split("@")[0],
                is_verified=True,
                consent_accepted_at=datetime.now(UTC),
            )
            user.profile = Profile()
            db.add(user)
            await db.flush()
            await log_action(
                db, "auth.register", user_id=user.id, details={"via": provider}, request=request
            )

    if account is None:
        account = OAuthAccount(
            user_id=user.id, provider=provider, provider_user_id=provider_user_id
        )
        db.add(account)

    # Refresh identity + tokens on every sign-in.
    account.email = email
    account.display_name = display_name
    account.picture_url = picture_url
    account.access_token_enc = crypto.encrypt(token.get("access_token"))
    if token.get("refresh_token"):  # Google only returns it on first consent
        account.refresh_token_enc = crypto.encrypt(token["refresh_token"])
    if token.get("expires_at"):
        account.token_expires_at = datetime.fromtimestamp(int(token["expires_at"]), tz=UTC)
    granted = token.get("scope", "")
    account.scopes = " ".join(sorted(set(account.scopes.split()) | set(granted.split())))

    user.last_login_at = datetime.now(UTC)
    await log_action(
        db, "auth.oauth_login", user_id=user.id, details={"provider": provider}, request=request
    )
    await db.commit()
    await db.refresh(user)
    return user


async def unlink_oauth_account(db: AsyncSession, user: User, provider: str) -> bool:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user.id, OAuthAccount.provider == provider
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        return False
    if not user.password_hash:
        # Don't strand the user without any way to log in.
        others = await db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user.id, OAuthAccount.provider != provider
            )
        )
        if others.first() is None:
            raise AuthError("Set a password before unlinking your only sign-in method.", 400)
    await db.delete(account)
    await log_action(db, "auth.oauth_unlink", user_id=user.id, details={"provider": provider})
    await db.commit()
    return True


async def delete_user_data(db: AsyncSession, user: User, request: Request | None) -> None:
    """GDPR-style erasure: delete the user and everything that cascades from it."""
    user_id, email = user.id, user.email
    await db.delete(user)
    # The audit row keeps a hashed-out reference only (user_id is SET NULL on delete).
    await log_action(
        db, "account.deleted", details={"email_domain": email.split("@")[-1]}, request=request
    )
    await db.commit()
    logger.info("Deleted all data for user %s", user_id)
