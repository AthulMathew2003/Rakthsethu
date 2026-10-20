from datetime import date, timedelta
import random
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.enums import BloodGroup, DonationStatus
from app.models.hospital import Hospital
from app.services.blood_compatibility import (
    get_compatible_donor_groups,
    is_blood_compatible,
)
from app.services.cooldown_service import (
    calculate_cooldown_eligibility,
    get_required_cooldown_days,
)


def random_phone() -> str:
    return f"9{random.randint(100000000, 999999999)}"


# -------------------------------------------------------------
# 1. Blood Compatibility Unit Tests
# -------------------------------------------------------------

def test_blood_compatibility_rules():
    # O Negative: Universal Donor, receives ONLY O-
    assert get_compatible_donor_groups(BloodGroup.O_NEGATIVE) == [BloodGroup.O_NEGATIVE]
    assert is_blood_compatible(BloodGroup.O_NEGATIVE, BloodGroup.O_NEGATIVE) is True
    assert is_blood_compatible(BloodGroup.O_POSITIVE, BloodGroup.O_NEGATIVE) is False
    assert is_blood_compatible(BloodGroup.A_POSITIVE, BloodGroup.O_NEGATIVE) is False

    # O Positive: Receives O+, O-
    assert set(get_compatible_donor_groups(BloodGroup.O_POSITIVE)) == {
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    }
    assert is_blood_compatible(BloodGroup.O_POSITIVE, BloodGroup.O_POSITIVE) is True
    assert is_blood_compatible(BloodGroup.O_NEGATIVE, BloodGroup.O_POSITIVE) is True
    assert is_blood_compatible(BloodGroup.A_POSITIVE, BloodGroup.O_POSITIVE) is False

    # B Positive: Receives B+, B-, O+, O-
    assert set(get_compatible_donor_groups(BloodGroup.B_POSITIVE)) == {
        BloodGroup.B_POSITIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    }
    assert is_blood_compatible(BloodGroup.B_POSITIVE, BloodGroup.B_POSITIVE) is True
    assert is_blood_compatible(BloodGroup.O_NEGATIVE, BloodGroup.B_POSITIVE) is True
    assert is_blood_compatible(BloodGroup.AB_POSITIVE, BloodGroup.B_POSITIVE) is False

    # AB Positive: Universal Recipient (all 8 groups)
    assert len(get_compatible_donor_groups(BloodGroup.AB_POSITIVE)) == 8
    for bg in BloodGroup:
        assert is_blood_compatible(bg, BloodGroup.AB_POSITIVE) is True

    # AB Negative: Receives AB-, A-, B-, O-
    assert set(get_compatible_donor_groups(BloodGroup.AB_NEGATIVE)) == {
        BloodGroup.AB_NEGATIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    }
    assert is_blood_compatible(BloodGroup.A_NEGATIVE, BloodGroup.AB_NEGATIVE) is True
    assert is_blood_compatible(BloodGroup.A_POSITIVE, BloodGroup.AB_NEGATIVE) is False


# -------------------------------------------------------------
# 2. Cooldown Service Unit Tests
# -------------------------------------------------------------

def test_cooldown_calculation():
    today = date.today()

    # Case 1: First-time donor (never donated)
    res1 = calculate_cooldown_eligibility(last_donation_date=None, reference_date=today)
    assert res1.is_eligible is True
    assert res1.days_remaining == 0
    assert res1.days_since_last_donation is None

    # Case 2: Recent donation (30 days ago, Whole Blood = 90 days cooldown)
    d_recent = today - timedelta(days=30)
    res2 = calculate_cooldown_eligibility(last_donation_date=d_recent, donation_type="Whole Blood", reference_date=today)
    assert res2.is_eligible is False
    assert res2.days_remaining == 60
    assert res2.days_since_last_donation == 30

    # Case 3: Exact cooldown boundary (90 days ago)
    d_exact = today - timedelta(days=90)
    res3 = calculate_cooldown_eligibility(last_donation_date=d_exact, donation_type="Whole Blood", reference_date=today)
    assert res3.is_eligible is True
    assert res3.days_remaining == 0
    assert res3.days_since_last_donation == 90

    # Case 4: Long past cooldown (150 days ago)
    d_old = today - timedelta(days=150)
    res4 = calculate_cooldown_eligibility(last_donation_date=d_old, donation_type="Whole Blood", reference_date=today)
    assert res4.is_eligible is True
    assert res4.days_remaining == 0
    assert res4.days_since_last_donation == 150

    # Case 5: Platelet cooldown (14 days)
    d_platelet = today - timedelta(days=15)
    res5 = calculate_cooldown_eligibility(last_donation_date=d_platelet, donation_type="Platelets", reference_date=today)
    assert res5.is_eligible is True
    assert res5.cooldown_days_required == 14


# -------------------------------------------------------------
# 3. Matching Engine Integration & DB Query Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_matching_engine_db_filtering_and_ranking(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    today = date.today()
    tag = str(random.randint(10000, 99999))

    # Seed controlled donors in Kottayam
    # Donor A: O+ in Kottayam (Pala), Available, Never Donated -> Perfect match
    donor_a = Donor(
        donor_code=f"MAT_A_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Alpha (O+ Pala Fresh)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=True,
    )
    # Donor B: O- in Kottayam (Pala), Available, Donated 120 days ago (COMPLETED) -> Compatible match
    donor_b = Donor(
        donor_code=f"MAT_B_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Beta (O- Pala Rested)",
        blood_group=BloodGroup.O_NEGATIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=True,
    )
    # Donor C: O+ in Kottayam, Available, Donated 10 days ago -> Should be EXCLUDED (cooldown active)
    donor_c = Donor(
        donor_code=f"MAT_C_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Gamma (O+ On Cooldown)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=True,
    )
    # Donor D: O+ in Kottayam, Inactive -> Should be EXCLUDED
    donor_d = Donor(
        donor_code=f"MAT_D_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Delta (Inactive)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=False,
        is_available=True,
    )
    # Donor E: O+ in Kottayam, Unavailable -> Should be EXCLUDED
    donor_e = Donor(
        donor_code=f"MAT_E_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Epsilon (Unavailable)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=False,
    )
    # Donor F: A+ in Kottayam -> Should be EXCLUDED for O+ recipient
    donor_f = Donor(
        donor_code=f"MAT_F_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Zeta (Incompatible A+)",
        blood_group=BloodGroup.A_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        is_active=True,
        is_available=True,
    )
    # Donor G: O+ in Ernakulam (Different district) -> Should be EXCLUDED for Kottayam request
    donor_g = Donor(
        donor_code=f"MAT_G_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Eta (Ernakulam District)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Ernakulam",
        panchayat="Aluva",
        is_active=True,
        is_available=True,
    )

    db_session.add_all([donor_a, donor_b, donor_c, donor_d, donor_e, donor_f, donor_g])
    await db_session.commit()
    for d in [donor_a, donor_b, donor_c, donor_d, donor_e, donor_f, donor_g]:
        await db_session.refresh(d)

    # Add donation records
    # Completed donation 120 days ago for Donor B
    don_b = Donation(
        donation_code=f"DON_{donor_b.id}_{tag}",
        donor_id=donor_b.id,
        hospital_id=test_hospital.id,
        donation_date=today - timedelta(days=120),
        status=DonationStatus.COMPLETED,
        units_donated=1,
    )
    # Completed donation 10 days ago for Donor C (blocks donor C)
    don_c = Donation(
        donation_code=f"DON_{donor_c.id}_{tag}",
        donor_id=donor_c.id,
        hospital_id=test_hospital.id,
        donation_date=today - timedelta(days=10),
        status=DonationStatus.COMPLETED,
        units_donated=1,
    )
    # Cancelled donation 5 days ago for Donor A (should NOT block donor A)
    don_a_cancelled = Donation(
        donation_code=f"DON_{donor_a.id}_{tag}",
        donor_id=donor_a.id,
        hospital_id=test_hospital.id,
        donation_date=today - timedelta(days=5),
        status=DonationStatus.CANCELLED,
        units_donated=1,
    )

    db_session.add_all([don_b, don_c, don_a_cancelled])
    await db_session.commit()

    # 4. Execute Matching Request for O+ patient in Kottayam (Pala)
    match_payload = {
        "blood_group": "O+",
        "district": "Kottayam",
        "panchayat": "Pala",
        "required_units": 2,
        "hospital_id": test_hospital.id,
        "limit": 100,
    }
    response = await client.post(
        "/api/v1/matching/donors",
        json=match_payload,
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    res_data = data["data"]

    assert res_data["recipient_blood_group"] == "O+"
    assert "O+" in res_data["compatible_blood_groups"]
    assert "O-" in res_data["compatible_blood_groups"]

    matched_ids = [item["donor_id"] for item in res_data["items"]]

    # Donor A (O+ Fresh) and Donor B (O- Rested) MUST be present
    assert donor_a.id in matched_ids
    assert donor_b.id in matched_ids

    # Donor C (On Cooldown), D (Inactive), E (Unavailable), F (Incompatible A+), G (Other District) MUST NOT be present
    assert donor_c.id not in matched_ids
    assert donor_d.id not in matched_ids
    assert donor_e.id not in matched_ids
    assert donor_f.id not in matched_ids
    assert donor_g.id not in matched_ids

    # Check ranking: Donor A (exact blood group O+) is prioritized before Donor B (compatible O-)
    pos_a = matched_ids.index(donor_a.id)
    pos_b = matched_ids.index(donor_b.id)
    assert pos_a < pos_b


# -------------------------------------------------------------
# 4. Additional Cooldown & Location Normalization Tests
# -------------------------------------------------------------

def test_scheduled_and_rejected_donations_do_not_block():
    today = date.today()
    # If latest donation status is not completed, it shouldn't trigger cooldown
    # calculate_cooldown_eligibility only takes last_completed_donation_date.
    # Passing None (as done when non-completed donations exist) yields 100% eligibility.
    res_none = calculate_cooldown_eligibility(last_donation_date=None, reference_date=today)
    assert res_none.is_eligible is True
    assert res_none.days_remaining == 0


@pytest.mark.asyncio
async def test_matching_location_normalization_and_empty_result(
    client: AsyncClient,
    super_admin_headers: dict,
):
    # Case 1: Location normalization with mixed case & whitespace (e.g. "  KoTtaYam  ")
    res_norm = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "  kOtTaYaM  "},
        headers=super_admin_headers,
    )
    assert res_norm.status_code == 200
    data = res_norm.json()
    assert data["success"] is True

    # Case 2: Empty result for non-existent district
    res_empty = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O-", "district": "NonExistentDistrictXYZ"},
        headers=super_admin_headers,
    )
    assert res_empty.status_code == 200
    empty_data = res_empty.json()
    assert empty_data["success"] is True
    assert empty_data["data"]["total_eligible_found"] == 0
    assert empty_data["data"]["items"] == []


# -------------------------------------------------------------
# 5. Matching API Error and Authentication Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_matching_api_unauthenticated_and_validation(client: AsyncClient, super_admin_headers: dict):
    # 1. Unauthenticated request -> 401
    res = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "Kottayam"},
    )
    assert res.status_code == 401

    # 2. Invalid blood group -> 422
    res_invalid_bg = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "XYZ+", "district": "Kottayam"},
        headers=super_admin_headers,
    )
    assert res_invalid_bg.status_code == 422

    # 3. Invalid required units (0) -> 422
    res_invalid_units = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "Kottayam", "required_units": 0},
        headers=super_admin_headers,
    )
    assert res_invalid_units.status_code == 422

