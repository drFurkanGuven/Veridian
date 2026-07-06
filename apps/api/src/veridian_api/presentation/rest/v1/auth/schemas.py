from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

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
    return UserResponse.model_validate(user)
