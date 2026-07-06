from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from veridian_api.domain.enums import AuditEventType, UserRole
from veridian_api.infrastructure.database.models.audit import AuditLog
from veridian_api.infrastructure.database.models.user import User
from veridian_api.services.audit_service import AuditService


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._audit = AuditService(db)

    @staticmethod
    def ensure_admin(user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise ForbiddenError("Admin access required")

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[User], int]:
        query = select(User)
        if search:
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(User.email).like(term),
                    func.lower(User.display_name).like(term),
                )
            )
        total = int(await self._db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        users = (
            await self._db.scalars(
                query.order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return list(users), total

    async def get_user(self, user_id: UUID) -> User:
        user = await self._db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def update_user(
        self,
        actor: User,
        user_id: UUID,
        *,
        is_active: Optional[bool] = None,
        role: Optional[UserRole] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        if actor.id == user_id and role is not None and role != UserRole.ADMIN:
            raise ValidationError("You cannot remove your own admin role")
        if actor.id == user_id and is_active is False:
            raise ValidationError("You cannot disable your own account")

        user = await self.get_user(user_id)
        if is_active is not None and user.is_active != is_active:
            user.is_active = is_active
            await self._audit.record(
                AuditEventType.ACCOUNT_ENABLED if is_active else AuditEventType.ACCOUNT_DISABLED,
                user_id=actor.id,
                target_user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        if role is not None and user.role != role:
            user.role = role
            await self._audit.record(
                AuditEventType.ROLE_CHANGED,
                user_id=actor.id,
                target_user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"role": role.value},
            )
        return user

    async def list_audit_logs(
        self,
        *,
        user_id: Optional[UUID] = None,
        event_type: Optional[AuditEventType] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        if user_id is not None:
            query = query.where(
                or_(AuditLog.user_id == user_id, AuditLog.target_user_id == user_id)
            )
        if event_type is not None:
            query = query.where(AuditLog.event_type == event_type)
        total = int(await self._db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        logs = (
            await self._db.scalars(
                query.order_by(AuditLog.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return list(logs), total
