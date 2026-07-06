import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_projects_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_create_project_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test FPGA"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_project_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401
