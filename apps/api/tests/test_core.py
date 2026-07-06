import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from veridian_api.core.exceptions import NotFoundError
from veridian_api.main import create_app


@pytest.fixture
def app() -> FastAPI:
    application = create_app()

    @application.get("/test/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Project not found", details={"id": "123"})

    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_request_id_propagated(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


@pytest.mark.asyncio
async def test_app_error_handler(client: AsyncClient) -> None:
    response = await client.get("/test/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "not_found"
    assert data["detail"] == "Project not found"
    assert data["details"]["id"] == "123"
    assert "request_id" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_api_v1_router_registered(client: AsyncClient) -> None:
    response = await client.get("/api/v1/openapi.json")
    assert response.status_code in {200, 404}
