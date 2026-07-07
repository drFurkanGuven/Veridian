import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_project_ai_conversations_requires_auth(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/ai/conversations"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_project_ai_conversation_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/ai/conversations",
        json={"title": "Test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_ai_messages_requires_auth(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/ai/conversations/00000000-0000-0000-0000-000000000002/messages"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_ai_conversation_requires_auth(client: AsyncClient) -> None:
    response = await client.delete(
        "/api/v1/ai/conversations/00000000-0000-0000-0000-000000000002"
    )
    assert response.status_code == 401
