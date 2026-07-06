from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Literal
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import asyncpg
import redis.asyncio as aioredis

from veridian_api.core.config import Settings, get_settings

ServiceStatus = Literal["ok", "error", "skipped"]


@dataclass(frozen=True)
class ServiceHealth:
    name: str
    status: ServiceStatus
    message: str | None = None


@dataclass(frozen=True)
class InfrastructureHealthReport:
    status: Literal["ready", "degraded"]
    services: list[ServiceHealth]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "services": [
                {"name": service.name, "status": service.status, "message": service.message}
                for service in self.services
            ],
        }


class InfrastructureHealthChecker:
    def __init__(self, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or get_settings()

    async def check(self) -> InfrastructureHealthReport:
        if not self._settings.health_check_infra:
            return InfrastructureHealthReport(
                status="ready",
                services=[ServiceHealth("infrastructure", "skipped", "checks disabled")],
            )

        results = await asyncio.gather(
            self._check_postgres(),
            self._check_redis(),
            self._check_rabbitmq(),
            self._check_minio(),
            self._check_database_schema(),
        )

        services = list(results)
        overall = "ready" if all(service.status == "ok" for service in services) else "degraded"
        return InfrastructureHealthReport(status=overall, services=services)

    async def _check_postgres(self) -> ServiceHealth:
        dsn = self._settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        try:
            connection = await asyncio.wait_for(asyncpg.connect(dsn=dsn), timeout=3.0)
            try:
                await connection.fetchval("SELECT 1")
            finally:
                await connection.close()
            return ServiceHealth("postgres", "ok")
        except Exception as exc:  # noqa: BLE001
            return ServiceHealth("postgres", "error", str(exc))

    async def _check_redis(self) -> ServiceHealth:
        client = aioredis.from_url(self._settings.redis_url, decode_responses=True)
        try:
            pong = await asyncio.wait_for(client.ping(), timeout=3.0)
            if pong:
                return ServiceHealth("redis", "ok")
            return ServiceHealth("redis", "error", "unexpected ping response")
        except Exception as exc:  # noqa: BLE001
            return ServiceHealth("redis", "error", str(exc))
        finally:
            await client.aclose()

    async def _check_rabbitmq(self) -> ServiceHealth:
        broker = urlparse(self._settings.celery_broker_url.replace("amqp://", "http://"))
        host = broker.hostname or "localhost"
        port = broker.port or 5672
        try:
            await asyncio.wait_for(self._check_tcp(host, port), timeout=3.0)
            return ServiceHealth("rabbitmq", "ok")
        except Exception as exc:  # noqa: BLE001
            return ServiceHealth("rabbitmq", "error", str(exc))

    async def _check_minio(self) -> ServiceHealth:
        health_url = f"{self._settings.s3_endpoint.rstrip('/')}/minio/health/live"
        try:
            await asyncio.wait_for(self._check_http(health_url), timeout=3.0)
            return ServiceHealth("minio", "ok")
        except Exception as exc:  # noqa: BLE001
            return ServiceHealth("minio", "error", str(exc))

    async def _check_database_schema(self) -> ServiceHealth:
        from sqlalchemy import text

        from veridian_api.infrastructure.database.session import engine

        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar_one_or_none()
                if not version:
                    return ServiceHealth("database_schema", "error", "no alembic revision applied")

                role_col = await connection.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'users' AND column_name = 'role'"
                    )
                )
                if role_col.scalar_one_or_none() is None:
                    return ServiceHealth(
                        "database_schema",
                        "error",
                        f"revision={version}; missing users.role — run pnpm db:migrate",
                    )

                audit_table = await connection.execute(text("SELECT to_regclass('public.audit_logs')"))
                if audit_table.scalar_one_or_none() is None:
                    return ServiceHealth(
                        "database_schema",
                        "error",
                        f"revision={version}; missing audit_logs — run pnpm db:migrate",
                    )

            return ServiceHealth("database_schema", "ok", f"revision={version}")
        except Exception as exc:  # noqa: BLE001
            return ServiceHealth("database_schema", "error", str(exc))

    async def _check_tcp(self, host: str, port: int) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._tcp_connect, host, port)

    @staticmethod
    def _tcp_connect(host: str, port: int) -> None:
        with socket.create_connection((host, port), timeout=3):
            return

    async def _check_http(self, url: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._http_get, url)

    @staticmethod
    def _http_get(url: str) -> None:
        try:
            with urlopen(url, timeout=3) as response:  # noqa: S310
                if response.status >= 400:
                    raise URLError(f"HTTP {response.status}")
        except URLError as exc:
            raise ConnectionError(str(exc)) from exc
