from datetime import date, timedelta
import random
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, hash_password
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.enums import BloodGroup, DonationStatus, RequestStatus, RequestUrgency, UserRole
from app.models.hospital import Hospital
from app.models.user import User


def random_phone() -> str:
    return f"9{random.randint(100000000, 999999999)}"


# -------------------------------------------------------------
# 1. Blood Request Lifecycle & Transitions
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_blood_request_lifecycle_valid_flow(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    today = date.today()

    # 1. Create request -> Defaults to PENDING
    create_payload = {
        "hospital_id": test_hospital.id,
        "patient_name": "Suresh Nair",
        "blood_group": "A+",
        "units_requested": 2,
        "district": "Kottayam",
        "location": "Pala",
        "contact_phone": "+919847012345",
        "required_date": str(today + timedelta(days=2)),
        "urgency": "URGENT",
    }
    res = await client.post("/api/v1/blood-requests", json=create_payload, headers=super_admin_headers)
    assert res.status_code == 201
    req_id = res.json()["data"]["id"]
    assert res.json()["data"]["status"] == "PENDING"

    # 2. Transition PENDING -> IN_PROGRESS
    res_in_prog = await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "IN_PROGRESS"},
        headers=super_admin_headers,
    )
    assert res_in_prog.status_code == 200
    assert res_in_prog.json()["data"]["status"] == "IN_PROGRESS"

    # 3. Transition IN_PROGRESS -> FULFILLED
    res_fulfilled = await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "FULFILLED"},
        headers=super_admin_headers,
    )
    assert res_fulfilled.status_code == 200
    assert res_fulfilled.json()["data"]["status"] == "FULFILLED"


@pytest.mark.asyncio
async def test_blood_request_illegal_transitions(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    today = date.today()

    # 1. Create request
    create_payload = {
        "hospital_id": test_hospital.id,
        "patient_name": "Radha Menon",
        "blood_group": "B+",
        "units_requested": 1,
        "district": "Kottayam",
        "contact_phone": "+919847098765",
        "required_date": str(today + timedelta(days=1)),
    }
    res = await client.post("/api/v1/blood-requests", json=create_payload, headers=super_admin_headers)
    assert res.status_code == 201
    req_id = res.json()["data"]["id"]

    # 2. Transition PENDING -> CANCELLED
    res_cancel = await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "CANCELLED"},
        headers=super_admin_headers,
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["data"]["status"] == "CANCELLED"

    # 3. Illegal transition: CANCELLED -> FULFILLED (Must be rejected)
    res_illegal = await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "FULFILLED"},
        headers=super_admin_headers,
    )
    assert res_illegal.status_code == 422
    assert res_illegal.json()["error"]["code"] == "VALIDATION_ERROR"

    # 4. Illegal transition: CANCELLED -> PENDING (Must be rejected)
    res_illegal_2 = await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "PENDING"},
        headers=super_admin_headers,
    )
    assert res_illegal_2.status_code == 422


# -------------------------------------------------------------
# 2. Request Matching Integration & State Enforcement
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_matching_integration(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital, db_session: AsyncSession
):
    today = date.today()
    tag = str(random.randint(10000, 99999))

    # Seed an available donor for B+
    donor = Donor(
        donor_code=f"REQ_MAT_{tag}",
        hospital_id=test_hospital.id,
        full_name="Matching Request Donor",
        blood_group=BloodGroup.B_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=True,
    )
    db_session.add(donor)
    await db_session.commit()

    # 1. Create a PENDING request
    res_req = await client.post(
        "/api/v1/blood-requests",
        json={
            "hospital_id": test_hospital.id,
            "patient_name": "Test Patient Match",
            "blood_group": "B+",
            "units_requested": 1,
            "district": "Kottayam",
            "location": "Pala",
            "contact_phone": "+919847055555",
            "required_date": str(today),
        },
        headers=super_admin_headers,
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["data"]["id"]

    # 2. Match donors for PENDING request -> Should succeed
    res_match = await client.get(f"/api/v1/blood-requests/{req_id}/matches", headers=super_admin_headers)
    assert res_match.status_code == 200
    match_data = res_match.json()["data"]
    assert match_data["recipient_blood_group"] == "B+"
    assert match_data["total_eligible_found"] >= 1

    # 3. Mark request FULFILLED
    await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "IN_PROGRESS"},
        headers=super_admin_headers,
    )
    await client.patch(
        f"/api/v1/blood-requests/{req_id}",
        json={"status": "FULFILLED"},
        headers=super_admin_headers,
    )

    # 4. Attempt to match donors for FULFILLED request -> Must be rejected with 422
    res_match_fulfilled = await client.get(
        f"/api/v1/blood-requests/{req_id}/matches",
        headers=super_admin_headers,
    )
    assert res_match_fulfilled.status_code == 422
    assert res_match_fulfilled.json()["error"]["code"] == "VALIDATION_ERROR"


# -------------------------------------------------------------
# 3. Donation Workflow, Validation & Cooldown Rules
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_donation_workflow_and_cooldown_rejection(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    today = date.today()
    phone = random_phone()

    # 1. Register a donor
    d_res = await client.post(
        "/api/v1/donors",
        json={
            "full_name": "Workflow Donor",
            "blood_group": "O+",
            "phone": phone,
            "district": "Kottayam",
        },
        headers=super_admin_headers,
    )
    assert d_res.status_code == 201
    donor_id = d_res.json()["data"]["id"]

    # 2. Schedule a future donation -> Allowed
    future_date = today + timedelta(days=5)
    sched_res = await client.post(
        "/api/v1/donations",
        json={
            "donor_id": donor_id,
            "hospital_id": test_hospital.id,
            "donation_date": str(future_date),
            "status": "SCHEDULED",
            "donation_type": "Whole Blood",
            "units_donated": 1,
        },
        headers=super_admin_headers,
    )
    assert sched_res.status_code == 201
    donation_id = sched_res.json()["data"]["id"]
    assert sched_res.json()["data"]["status"] == "SCHEDULED"

    # 3. Attempt to mark future donation COMPLETED while date is in the future -> Rejected
    fail_future = await client.patch(
        f"/api/v1/donations/{donation_id}",
        json={"status": "COMPLETED"},
        headers=super_admin_headers,
    )
    assert fail_future.status_code == 422
    assert fail_future.json()["error"]["code"] == "VALIDATION_ERROR"

    # 4. Update date to today and mark COMPLETED -> Allowed
    comp_res = await client.patch(
        f"/api/v1/donations/{donation_id}",
        json={"donation_date": str(today), "status": "COMPLETED"},
        headers=super_admin_headers,
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["data"]["status"] == "COMPLETED"

    # 5. Attempt to mutate COMPLETED donation back to SCHEDULED or CANCELLED -> Rejected
    res_reverse = await client.patch(
        f"/api/v1/donations/{donation_id}",
        json={"status": "SCHEDULED"},
        headers=super_admin_headers,
    )
    assert res_reverse.status_code == 422

    # 6. Attempt to record another COMPLETED donation 10 days later for same donor -> Rejected by Cooldown
    res_cooldown_block = await client.post(
        "/api/v1/donations",
        json={
            "donor_id": donor_id,
            "hospital_id": test_hospital.id,
            "donation_date": str(today),
            "status": "COMPLETED",
            "donation_type": "Whole Blood",
            "units_donated": 1,
        },
        headers=super_admin_headers,
    )
    assert res_cooldown_block.status_code == 422
    assert "cooldown" in res_cooldown_block.json()["message"].lower()


# -------------------------------------------------------------
# 4. RBAC & Cross-Hospital Scoping IDOR Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_cross_hospital_idor_prevention(
    client: AsyncClient,
    hospital_admin_headers: dict,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    today = date.today()

    # 1. Create a second hospital (Hospital B)
    hosp_code = f"HOSP_B_{random.randint(10000, 99999)}"
    hospital_b = Hospital(
        hospital_code=hosp_code,
        name="Ernakulam General Hospital",
        hospital_type="Government",
        district="Ernakulam",
        address="Park Avenue, Ernakulam",
        phone="+914842361234",
        is_active=True,
    )
    db_session.add(hospital_b)
    await db_session.commit()
    await db_session.refresh(hospital_b)

    # 2. Create a blood request belonging to Hospital B
    req_b = {
        "hospital_id": hospital_b.id,
        "patient_name": "Hospital B Patient",
        "blood_group": "AB+",
        "units_requested": 1,
        "district": "Ernakulam",
        "contact_phone": "+919847066666",
        "required_date": str(today),
    }

    res_b = await client.post("/api/v1/blood-requests", json=req_b, headers=super_admin_headers)
    assert res_b.status_code == 201
    req_b_id = res_b.json()["data"]["id"]

    # 3. Hospital Admin (from Hospital A) attempts to update Hospital B's request -> 403 Forbidden
    res_update_attack = await client.patch(
        f"/api/v1/blood-requests/{req_b_id}",
        json={"status": "IN_PROGRESS"},
        headers=hospital_admin_headers,
    )
    assert res_update_attack.status_code == 403
    assert res_update_attack.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"

    # 4. Hospital Admin (from Hospital A) attempts to match Hospital B's request -> 403 Forbidden
    res_match_attack = await client.get(
        f"/api/v1/blood-requests/{req_b_id}/matches",
        headers=hospital_admin_headers,
    )
    assert res_match_attack.status_code == 403
    assert res_match_attack.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"
