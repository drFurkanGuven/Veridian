from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from veridian_api.domain.enums import AuditEventType
from veridian_api.infrastructure.auth.password import hash_password, verify_password
from veridian_api.infrastructure.auth.password_policy import validate_password
from veridian_api.infrastructure.auth.tokens import hash_token
from veridian_api.infrastructure.database.models.oauth import UserSession
from veridian_api.infrastructure.database.models.user import User
from veridian_api.services.audit_service import AuditService


class AccountService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._audit = AuditService(db)

    async def list_sessions(self, user_id: UUID) -> list[UserSession]:
        now = datetime.now(timezone.utc)
        sessions = (
            await self._db.scalars(
                select(UserSession)
                .where(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > now,
                )
                .order_by(UserSession.created_at.desc())
            )
        ).all()
        return list(sessions)

    async def revoke_session(
        self,
        user_id: UUID,
        session_id: UUID,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        session = await self._db.scalar(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        )
        if session is None:
            raise NotFoundError("Session not found")
        session.revoked_at = datetime.now(timezone.utc)
        await self._audit.record(
            AuditEventType.SESSION_REVOKED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"sessionId": str(session_id)},
        )

    async def revoke_other_sessions(
        self,
        user_id: UUID,
        current_refresh_token: str,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> int:
        current_hash = hash_token(current_refresh_token)
        now = datetime.now(timezone.utc)
        sessions = (
            await self._db.scalars(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > now,
                    UserSession.token_hash != current_hash,
                )
            )
        ).all()
        revoked = 0
        for session in sessions:
            session.revoked_at = now
            revoked += 1
        if revoked:
            await self._audit.record(
                AuditEventType.SESSION_REVOKED,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"revokedCount": revoked, "scope": "others"},
            )
        return revoked

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        if not user.password_hash:
            raise ValidationError("Password login is not enabled for this account")
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        validate_password(new_password, min_length=self._settings.auth_min_password_length)
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self._audit.record(
            AuditEventType.PASSWORD_CHANGED,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def update_profile(
        self,
        user: User,
        display_name: str,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        cleaned = display_name.strip()
        if not cleaned:
            raise ValidationError("displayName is required")
        user.display_name = cleaned
        await self._audit.record(
            AuditEventType.PROFILE_UPDATED,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"displayName": cleaned},
        )
        return user
