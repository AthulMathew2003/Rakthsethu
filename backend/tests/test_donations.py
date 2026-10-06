import time
import pytest
from httpx import AsyncClient
from app.models.hospital import Hospital


@pytest.mark.asyncio
async def test_create_donation_success(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    # 1. Create donor
    ts = str(int(time.time() * 1000))[-8:]
    d_res = await client.post(
        "/api/v1/donors",
        json={
            "full_name": "Donation Tester",
            "blood_group": "B+",
            "phone": f"+9197{ts}",
            "district": "Kottayam",
        },
        headers=super_admin_headers,
    )
    donor_id = d_res.json()["data"]["id"]

    # 2. Record donation
    payload = {
        "donor_id": donor_id,
        "hospital_id": test_hospital.id,
        "donation_date": "2026-08-15",
        "donation_type": "Voluntary",
        "units_donated": 1,
        "status": "COMPLETED",
        "notes": "Camp collection",
    }
    response = await client.post("/api/v1/donations", json=payload, headers=super_admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["donor_id"] == donor_id
    assert data["data"]["units_donated"] == 1
    assert data["data"]["donation_date"] == "2026-08-15"


@pytest.mark.asyncio
async def test_create_donation_invalid_donor(
    client: AsyncClient, super_admin_headers: dict
):
    payload = {
        "donor_id": 999999,  # Non-existent donor
        "donation_date": "2026-08-15",
        "units_donated": 1,
    }
    response = await client.post("/api/v1/donations", json=payload, headers=super_admin_headers)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_donation_invalid_units(
    client: AsyncClient, super_admin_headers: dict
):
    payload = {
        "donor_id": 1,
        "donation_date": "2026-08-15",
        "units_donated": 0,  # Invalid
    }
    response = await client.post("/api/v1/donations", json=payload, headers=super_admin_headers)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
