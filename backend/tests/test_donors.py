import time
import pytest
from httpx import AsyncClient
from app.models.hospital import Hospital


@pytest.mark.asyncio
async def test_create_donor_success_and_phone_normalization(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    ts = str(int(time.time() * 1000))[-8:]
    phone_raw = f"98{ts}"
    payload = {
        "full_name": "Athul Krishna",
        "blood_group": "O+",
        "phone": phone_raw,  # 10 digits
        "district": "Kottayam",
        "hospital_id": test_hospital.id,
        "is_available": True,
    }
    response = await client.post("/api/v1/donors", json=payload, headers=super_admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    # Verify phone was normalized to +9198XXXXXXXX
    assert data["data"]["phone"] == f"+91{phone_raw}"
    assert data["data"]["blood_group"] == "O+"
    assert data["data"]["is_active"] is True
    assert data["data"]["is_available"] is True


@pytest.mark.asyncio
async def test_create_donor_duplicate_phone(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    ts = str(int(time.time() * 1000))[-8:]
    phone_raw = f"99{ts}"
    payload1 = {
        "full_name": "First Donor",
        "blood_group": "A+",
        "phone": f"+91{phone_raw}",
        "district": "Kottayam",
    }
    resp1 = await client.post("/api/v1/donors", json=payload1, headers=super_admin_headers)
    assert resp1.status_code == 201

    # Attempt duplicate phone with 10-digit format without prefix
    payload2 = {
        "full_name": "Second Donor Attempt",
        "blood_group": "B+",
        "phone": phone_raw,
        "district": "Ernakulam",
    }
    resp2 = await client.post("/api/v1/donors", json=payload2, headers=super_admin_headers)
    assert resp2.status_code == 409
    data = resp2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DUPLICATE_RESOURCE"


@pytest.mark.asyncio
async def test_create_donor_invalid_blood_group(
    client: AsyncClient, super_admin_headers: dict
):
    payload = {
        "full_name": "Invalid Blood Group Donor",
        "blood_group": "C+",  # Invalid ABO/Rh
        "phone": "+919847088888",
        "district": "Kottayam",
    }
    response = await client.post("/api/v1/donors", json=payload, headers=super_admin_headers)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_list_donors_filter_by_group_and_district(
    client: AsyncClient, super_admin_headers: dict
):
    ts = str(int(time.time() * 1000))[-7:]
    # Seed donors
    await client.post(
        "/api/v1/donors",
        json={
            "full_name": "Kottayam O- Positive",
            "blood_group": "O-",
            "phone": f"+9191{ts}1",
            "district": "Kottayam",
            "is_available": True,
        },
        headers=super_admin_headers,
    )
    await client.post(
        "/api/v1/donors",
        json={
            "full_name": "Ernakulam AB+ Positive",
            "blood_group": "AB+",
            "phone": f"+9191{ts}2",
            "district": "Ernakulam",
            "is_available": True,
        },
        headers=super_admin_headers,
    )

    # Filter for O- in Kottayam
    response = await client.get(
        "/api/v1/donors?blood_group=O-&district=Kottayam",
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    items = data["data"]["items"]
    assert len(items) >= 1
    for d in items:
        assert d["blood_group"] == "O-"
        assert d["district"] == "Kottayam"
