from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from veridian_api.domain.enums import UserRole
from veridian_api.infrastructure.database.models.oauth import UserSession
from veridian_api.infrastructure.database.models.user import User


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class UserResponse(CamelModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: Optional[str]
    email_verified: bool
    role: UserRole
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime


class AuthTokensResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(CamelModel):
    user: UserResponse
    tokens: AuthTokensResponse


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(CamelModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(CamelModel):
    refresh_token: str = Field(min_length=1)


class UpdateProfileRequest(CamelModel):
    display_name: str = Field(min_length=1, max_length=100)


class ChangePasswordRequest(CamelModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RevokeOtherSessionsRequest(CamelModel):
    refresh_token: str = Field(min_length=1)


class SessionResponse(CamelModel):
    id: UUID
    user_agent: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    expires_at: datetime


class SessionListResponse(CamelModel):
    items: list[SessionResponse]


class RevokeOthersResponse(CamelModel):
    revoked_count: int


class OAuthUrlResponse(CamelModel):
    url: str
    state: str


class OAuthCallbackRequest(CamelModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class OAuthProvidersResponse(CamelModel):
    google: bool
    github: bool
    google_redirect_uri: Optional[str] = None
    github_redirect_uri: Optional[str] = None


def user_to_response(user: User) -> UserResponse:
    role = user.role if user.role is not None else UserRole.USER
    is_active = True if user.is_active is None else user.is_active
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
        role=role,
        is_active=is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def session_to_response(session: UserSession) -> SessionResponse:
    return SessionResponse.model_validate(session)
