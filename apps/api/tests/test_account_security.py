import pytest
from httpx import ASGITransport, AsyncClient

from veridian_api.core.exceptions import ValidationError
from veridian_api.infrastructure.auth.password_policy import validate_password
from veridian_api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_password_policy_requires_letter_and_digit() -> None:
    with pytest.raises(ValidationError):
        validate_password("12345678")
    with pytest.raises(ValidationError):
        validate_password("abcdefgh")
    validate_password("abc12345")


@pytest.mark.asyncio
async def test_admin_users_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_sessions_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "oldpass1", "newPassword": "newpass12"},
    )
    assert response.status_code == 401
