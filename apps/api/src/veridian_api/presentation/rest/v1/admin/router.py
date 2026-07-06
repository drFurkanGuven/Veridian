from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from veridian_api.core.deps import get_current_admin, get_db
from veridian_api.domain.enums import AuditEventType
from veridian_api.infrastructure.database.models.user import User
from veridian_api.presentation.rest.v1.admin.schemas import (
    AdminUserListResponse,
    AdminUserResponse,
    AuditLogListResponse,
    UpdateAdminUserRequest,
    admin_user_to_response,
    audit_log_to_response,
)
from veridian_api.presentation.rest.v1.auth.router import _client_meta
from veridian_api.services.admin_service import AdminService

router = APIRouter()


def get_admin_service(db=Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    search: Optional[str] = Query(None),
    _: User = Depends(get_current_admin),
    admin: AdminService = Depends(get_admin_service),
) -> AdminUserListResponse:
    users, total = await admin.list_users(page=page, page_size=page_size, search=search)
    return AdminUserListResponse(
        items=[admin_user_to_response(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    _: User = Depends(get_current_admin),
    admin: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    user = await admin.get_user(user_id)
    return admin_user_to_response(user)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    body: UpdateAdminUserRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
    admin: AdminService = Depends(get_admin_service),
) -> AdminUserResponse:
    user_agent, ip_address = _client_meta(request)
    user = await admin.update_user(
        actor,
        user_id,
        is_active=body.is_active,
        role=body.role,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return admin_user_to_response(user)


@router.get("/audit", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    user_id: Optional[UUID] = Query(None, alias="userId"),
    event_type: Optional[AuditEventType] = Query(None, alias="eventType"),
    _: User = Depends(get_current_admin),
    admin: AdminService = Depends(get_admin_service),
) -> AuditLogListResponse:
    logs, total = await admin.list_audit_logs(
        user_id=user_id,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[audit_log_to_response(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )
