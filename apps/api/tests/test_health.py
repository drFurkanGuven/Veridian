import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.core.config import Settings, get_settings
from veridian_api.infrastructure.health import InfrastructureHealthChecker
from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_readiness_check_when_infra_disabled(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["services"][0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_readiness_check_with_infra_enabled() -> None:
    checker = InfrastructureHealthChecker(Settings(health_check_infra=True))
    report = await checker.check()
    assert report.status in {"ready", "degraded"}
    assert len(report.services) == 5
    service_names = {service.name for service in report.services}
    assert service_names == {"postgres", "redis", "rabbitmq", "minio", "database_schema"}
