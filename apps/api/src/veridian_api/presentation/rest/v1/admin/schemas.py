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
    return AdminUserResponse.model_validate(user)


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
