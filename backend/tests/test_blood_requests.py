import pytest
from httpx import AsyncClient
from app.models.hospital import Hospital


@pytest.mark.asyncio
async def test_create_blood_request_success(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    payload = {
        "hospital_id": test_hospital.id,
        "patient_name": "Emergency Patient Case #102",
        "blood_group": "AB-",
        "units_requested": 2,
        "district": "Kottayam",
        "location": "ICU Bed 4",
        "contact_phone": "+919847055555",
        "required_date": "2026-09-30",
        "urgency": "CRITICAL",
        "status": "PENDING",
    }
    response = await client.post(
        "/api/v1/blood-requests", json=payload, headers=super_admin_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["patient_name"] == "Emergency Patient Case #102"
    assert data["data"]["blood_group"] == "AB-"
    assert data["data"]["urgency"] == "CRITICAL"


@pytest.mark.asyncio
async def test_create_blood_request_invalid_units(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    payload = {
        "hospital_id": test_hospital.id,
        "patient_name": "Patient Zero",
        "blood_group": "O+",
        "units_requested": 0,  # Invalid
        "district": "Kottayam",
        "contact_phone": "+919847055555",
        "required_date": "2026-09-30",
    }
    response = await client.post(
        "/api/v1/blood-requests", json=payload, headers=super_admin_headers
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_list_blood_requests_filter(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    response = await client.get(
        f"/api/v1/blood-requests?hospital_id={test_hospital.id}&urgency=CRITICAL",
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"]["items"], list)
