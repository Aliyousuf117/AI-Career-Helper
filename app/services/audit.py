"""Audit logging: every security-relevant or external action is recorded here."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import client_ip
from app.models import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    action: str,
    *,
    user_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    """Append an audit entry. Caller is responsible for committing the session."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip=client_ip(request) if request else None,
        user_agent=(request.headers.get("user-agent", "")[:300] if request else None),
    )
    db.add(entry)
    logger.info("audit %s user=%s entity=%s/%s", action, user_id, entity_type, entity_id)
    return entry
