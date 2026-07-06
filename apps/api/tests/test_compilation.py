import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_compile_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/compile",
        json={"topModule": "top"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_job_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_job_logs_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000001/logs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_artifact_requires_auth(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000001"
        "/artifacts/00000000-0000-0000-0000-000000000002/download"
    )
    assert response.status_code == 401
