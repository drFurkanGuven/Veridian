from __future__ import annotations

from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from veridian_api.core.config import Settings, get_settings


def apply_cors_headers(
    request: Request,
    response: Response,
    settings: Optional[Settings] = None,
) -> Response:
    settings = settings or get_settings()
    origin = request.headers.get("origin")
    if not origin:
        return response

    allowed = set(settings.cors_origins)
    if origin not in allowed:
        return response

    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers.setdefault("Vary", "Origin")
    response.headers.setdefault(
        "Access-Control-Expose-Headers",
        "X-Request-ID, Retry-After",
    )
    return response


def cors_json_response(
    request: Request,
    *,
    status_code: int,
    content: dict,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content, headers=headers or {})
    return apply_cors_headers(request, response)  # type: ignore[return-value]
