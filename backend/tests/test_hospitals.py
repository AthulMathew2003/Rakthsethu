import pytest
from httpx import AsyncClient
from app.models.hospital import Hospital


@pytest.mark.asyncio
async def test_create_hospital_success(client: AsyncClient, super_admin_headers: dict):
    payload = {
        "name": "General Hospital Ernakulam",
        "hospital_type": "Government",
        "district": "Ernakulam",
        "address": "Hospital Road, Ernakulam, Kerala",
        "phone": "+914842361251",
    }
    response = await client.post("/api/v1/hospitals", json=payload, headers=super_admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "General Hospital Ernakulam"
    assert "hospital_code" in data["data"]


@pytest.mark.asyncio
async def test_create_hospital_forbidden_for_staff(client: AsyncClient, hospital_admin_headers: dict):
    payload = {
        "name": "Unauthorized Hospital Attempt",
        "district": "Idukki",
        "address": "Munnar, Kerala",
    }
    response = await client.post("/api/v1/hospitals", json=payload, headers=hospital_admin_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_get_hospital_by_id(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    response = await client.get(
        f"/api/v1/hospitals/{test_hospital.id}", headers=super_admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == test_hospital.id
    assert data["data"]["name"] == test_hospital.name


@pytest.mark.asyncio
async def test_list_hospitals(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    response = await client.get("/api/v1/hospitals?district=Kottayam", headers=super_admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1
