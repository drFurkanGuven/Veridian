from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from veridian_api.core.cors import cors_json_response
from veridian_api.core.exceptions import AppError, RateLimitError

logger = logging.getLogger(__name__)


def _error_body(
    *,
    detail: str,
    code: str,
    status_code: int,
    request_id: str,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "detail": detail,
        "code": code,
        "status_code": status_code,
        "request_id": request_id,
    }
    if details:
        body["details"] = details
    return body


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers: dict[str, str] = {"X-Request-ID": _request_id(request)}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return cors_json_response(
        request,
        status_code=exc.status_code,
        content=_error_body(
            detail=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            request_id=_request_id(request),
            details=exc.details,
        ),
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return cors_json_response(
        request,
        status_code=422,
        content=_error_body(
            detail="Request validation failed",
            code="validation_error",
            status_code=422,
            request_id=_request_id(request),
            details={"errors": exc.errors()},
        ),
        headers={"X-Request-ID": _request_id(request)},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return cors_json_response(
        request,
        status_code=exc.status_code,
        content=_error_body(
            detail=str(exc.detail),
            code="http_error",
            status_code=exc.status_code,
            request_id=_request_id(request),
        ),
        headers={"X-Request-ID": _request_id(request)},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error [%s] %s", _request_id(request), request.url.path)
    return cors_json_response(
        request,
        status_code=500,
        content=_error_body(
            detail="Internal server error",
            code="internal_error",
            status_code=500,
            request_id=_request_id(request),
        ),
        headers={"X-Request-ID": _request_id(request)},
    )
