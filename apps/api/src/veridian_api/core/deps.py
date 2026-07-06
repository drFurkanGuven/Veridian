from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from veridian_api.core.config import Settings, get_settings
from veridian_api.infrastructure.cache.redis import get_redis_client
from veridian_api.infrastructure.database.session import get_session

__all__ = [
    "get_db",
    "get_redis",
    "get_request_id",
    "get_settings_dep",
]


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
