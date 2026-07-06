from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings, get_settings
from veridian_api.core.exceptions import ForbiddenError, UnauthorizedError
from veridian_api.domain.enums import UserRole
from veridian_api.infrastructure.cache.redis import get_redis_client
from veridian_api.infrastructure.database.models.user import User
from veridian_api.infrastructure.database.session import get_session
from veridian_api.services.auth_service import AuthService

__all__ = [
    "get_current_admin",
    "get_current_user",
    "get_db",
    "get_redis",
    "get_request_id",
    "get_settings_dep",
]

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_redis():
    return await get_redis_client()


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        return "unknown"
    return str(request_id)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer token")

    auth = AuthService(db, settings)
    user_id = auth.decode_access_token(credentials.credentials, settings)
    return await auth.get_user_by_id(user_id)


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user
