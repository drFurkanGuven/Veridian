from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from veridian_api.domain.enums import AuditEventType, UserRole
from veridian_api.infrastructure.database.models.audit import AuditLog
from veridian_api.infrastructure.database.models.user import User


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class AdminUserResponse(CamelModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: Optional[str]
    email_verified: bool
    role: UserRole
    is_active: bool
    failed_login_attempts: int
    locked_until: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime


class AdminUserListResponse(CamelModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class UpdateAdminUserRequest(CamelModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class AuditLogResponse(CamelModel):
    id: int
    user_id: Optional[UUID]
    target_user_id: Optional[UUID]
    event_type: AuditEventType
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[dict[str, Any]] = Field(default=None, validation_alias="metadata_json")
    created_at: datetime


class AuditLogListResponse(CamelModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


def admin_user_to_response(user: User) -> AdminUserResponse:
    role = user.role if user.role is not None else UserRole.USER
    is_active = True if user.is_active is None else user.is_active
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
        role=role,
        is_active=is_active,
        failed_login_attempts=user.failed_login_attempts or 0,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def audit_log_to_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        target_user_id=log.target_user_id,
        event_type=log.event_type,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        metadata=log.metadata_json,
        created_at=log.created_at,
    )
