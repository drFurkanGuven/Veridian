import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_simulate_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/simulate",
        json={
            "simulator": "icarus",
            "testbenchFileId": "00000000-0000-0000-0000-000000000002",
            "topModule": "top",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_simulations_requires_auth(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/simulations",
    )
    assert response.status_code == 401
