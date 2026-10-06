import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, super_admin_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@test.com", "password": "adminpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "superadmin@test.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, super_admin_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@test.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_auth_me_success(client: AsyncClient, super_admin_headers: dict):
    response = await client.get("/api/v1/auth/me", headers=super_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "superadmin@test.com"
    assert data["data"]["role"] == "SUPER_ADMIN"


@pytest.mark.asyncio
async def test_auth_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_123"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
