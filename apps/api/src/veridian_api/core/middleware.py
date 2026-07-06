import logging
import time
import uuid
from collections.abc import Callable
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from veridian_api.core.config import get_settings
from veridian_api.core.cors import cors_json_response
from veridian_api.core.exceptions import RateLimitError
from veridian_api.infrastructure.cache.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

RATE_LIMIT_EXEMPT_PATHS = {
    "/health",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        if request.url.path in RATE_LIMIT_EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        client_key = f"{_client_ip(request)}:{request.url.path}"
        try:
            allowed, retry_after = await self._rate_limiter.check_request(client_key)
        except Exception:
            logger.exception("Rate limiter unavailable — allowing request")
            return await call_next(request)

        if not allowed:
            error = RateLimitError(retry_after=retry_after)
            return cors_json_response(
                request,
                status_code=error.status_code,
                content={
                    "detail": error.message,
                    "code": error.code,
                    "status_code": error.status_code,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": getattr(request.state, "request_id", ""),
                },
            )

        return await call_next(request)
