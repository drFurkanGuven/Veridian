from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.domain.enums import AuditEventType
from veridian_api.infrastructure.database.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        event_type: AuditEventType,
        *,
        user_id: Optional[UUID] = None,
        target_user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self._db.add(
            AuditLog(
                user_id=user_id,
                target_user_id=target_user_id,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json=metadata,
            )
        )
        await self._db.flush()

    async def record_safe(
        self,
        event_type: AuditEventType,
        *,
        user_id: Optional[UUID] = None,
        target_user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            await self.record(
                event_type,
                user_id=user_id,
                target_user_id=target_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
            )
        except Exception:
            logger.exception("Audit log write failed for %s", event_type.value)


def coerce_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
