from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from veridian_api import __version__
from veridian_api.core.config import get_settings, settings
from veridian_api.core.exceptions import AppError
from veridian_api.core.logging import setup_logging
from veridian_api.core.middleware import (
    RateLimitMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)
from veridian_api.infrastructure.cache.redis import close_redis_client
from veridian_api.infrastructure.database.session import engine
from veridian_api.presentation.exception_handlers import (
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from veridian_api.presentation.rest.health import router as health_router
from veridian_api.presentation.rest.router import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(get_settings())
    logger.info("Starting %s API v%s", settings.app_name, __version__)
    yield
    await close_redis_client()
    await engine.dispose()
    logger.info("Shutdown complete")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Veridian API",
        description="Veridian cloud IDE backend",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.api_debug else None,
        redoc_url="/redoc" if settings.api_debug else None,
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "veridian_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )


if __name__ == "__main__":
    run()
