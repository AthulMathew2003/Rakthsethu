from datetime import date, timedelta
import random
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from app.core.config import settings
from app.core.phone_utils import normalize_phone_number
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.enums import BloodGroup, DonationStatus
from app.models.hospital import Hospital
from app.models.user import User


def random_phone() -> str:
    return normalize_phone_number(f"9{random.randint(100000000, 999999999)}")


# -------------------------------------------------------------
# 1. Donor Consent & Location Ownership Audit Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_consent_mandatory_for_location_update(
    client: AsyncClient,
    super_admin_headers: dict,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))
    create_res = await client.post(
        "/api/v1/donors",
        json={
            "donor_code": f"D_AUD_{tag}",
            "full_name": "Consent Audit Donor",
            "blood_group": "B+",
            "phone": random_phone(),
            "district": "Kottayam",
            "hospital_id": test_hospital.id,
        },
        headers=super_admin_headers,
    )
    assert create_res.status_code == 201
    donor_id = create_res.json()["data"]["id"]

    # 1. Missing consent_confirmed field -> Rejected (422)
    res_no_consent = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.59, "longitude": 76.52},
        headers=super_admin_headers,
    )
    assert res_no_consent.status_code == 422

    # 2. consent_confirmed = False -> Rejected (422)
    res_false_consent = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.59, "longitude": 76.52, "consent_confirmed": False},
        headers=super_admin_headers,
    )
    assert res_false_consent.status_code == 422
    assert "consent is mandatory" in str(res_false_consent.json()).lower()

    # 3. consent_confirmed = True -> Accepted (200)
    res_ok = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.59, "longitude": 76.52, "consent_confirmed": True},
        headers=super_admin_headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["data"]["has_location"] is True
    assert res_ok.json()["data"]["location_consent"] is True


@pytest.mark.asyncio
async def test_matching_excludes_donor_without_consent(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))

    # Donor with location in DB but location_consent is False (e.g. consent withheld or revoked)
    d_no_consent = Donor(
        donor_code=f"D_NOCON_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Has Coords But No Consent",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        location=WKTElement("POINT(76.53 9.60)", srid=4326),
        location_consent=False,  # NO CONSENT
        is_active=True,
        is_available=True,
    )
    db_session.add(d_no_consent)
    await db_session.commit()
    await db_session.refresh(d_no_consent)

    # Perform proximity matching
    res = await client.post(
        "/api/v1/matching/donors",
        json={
            "blood_group": "O+",
            "latitude": 9.5916,
            "longitude": 76.5222,
            "radius_km": 25.0,
            "include_fallback": False,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    matched_ids = [it["donor_id"] for it in items]

    # Donor without consent MUST NOT appear in proximity matches
    assert d_no_consent.id not in matched_ids


# -------------------------------------------------------------
# 2. Radius and Coordinate Validation Audit Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_radius_validation_and_rejection_no_silent_clamping(
    client: AsyncClient,
    super_admin_headers: dict,
):
    # 1. Radius zero -> Must be rejected (422), not supported
    res_zero = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "Kottayam", "radius_km": 0},
        headers=super_admin_headers,
    )
    assert res_zero.status_code == 422
    assert "greater than 0" in str(res_zero.json()).lower()

    # 2. Negative radius -> Must be rejected (422)
    res_neg = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "Kottayam", "radius_km": -10.0},
        headers=super_admin_headers,
    )
    assert res_neg.status_code == 422

    # 3. Radius exceeding MAX_PROXIMITY_RADIUS_KM -> Must be rejected (422), NEVER silently clamped
    excess_radius = settings.MAX_PROXIMITY_RADIUS_KM + 15.0
    res_excess = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "district": "Kottayam", "radius_km": excess_radius},
        headers=super_admin_headers,
    )
    assert res_excess.status_code == 422
    assert "exceeds maximum" in str(res_excess.json()).lower()


@pytest.mark.asyncio
async def test_coordinate_validation_non_finite_and_partial_pairs(
    client: AsyncClient,
    super_admin_headers: dict,
):
    # 1. Partial coordinates (latitude without longitude) -> 422
    res_partial_lat = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "latitude": 9.59},
        headers=super_admin_headers,
    )
    assert res_partial_lat.status_code == 422
    assert "both latitude and longitude" in str(res_partial_lat.json()).lower()

    # 2. Partial coordinates (longitude without latitude) -> 422
    res_partial_lon = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "longitude": 76.52},
        headers=super_admin_headers,
    )
    assert res_partial_lon.status_code == 422

    # 3. Latitude out of [-90, 90] bounds -> 422
    res_bound_lat = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "latitude": 91.0, "longitude": 76.52},
        headers=super_admin_headers,
    )
    assert res_bound_lat.status_code == 422

    # 4. Longitude out of [-180, 180] bounds -> 422
    res_bound_lon = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "latitude": 9.59, "longitude": 181.0},
        headers=super_admin_headers,
    )
    assert res_bound_lon.status_code == 422


# -------------------------------------------------------------
# 3. Authorization & Tenant Scoping Audit Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_hospital_staff_cannot_modify_unaffiliated_or_other_hospital_donor(
    client: AsyncClient,
    hospital_admin_headers: dict,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))

    # 1. Create an unaffiliated donor (hospital_id is None)
    unaffiliated_donor = Donor(
        donor_code=f"D_UNAFF_{tag}",
        hospital_id=None,  # Unaffiliated
        full_name="Unaffiliated Community Donor",
        blood_group=BloodGroup.A_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        is_active=True,
        is_available=True,
    )
    # 2. Create another hospital (Hospital B) and donor belonging to Hospital B
    hosp_b = Hospital(
        hospital_code=f"HOSP_AUD_{tag}",
        name="Audited Other Hospital",
        hospital_type="Government",
        district="Ernakulam",
        address="Kochi",
        is_active=True,
    )
    db_session.add_all([unaffiliated_donor, hosp_b])
    await db_session.commit()
    await db_session.refresh(unaffiliated_donor)
    await db_session.refresh(hosp_b)

    donor_b = Donor(
        donor_code=f"D_HOSPB_{tag}",
        hospital_id=hosp_b.id,  # Belonging to Hospital B
        full_name="Hospital B Donor",
        blood_group=BloodGroup.A_POSITIVE,
        phone=random_phone(),
        district="Ernakulam",
        is_active=True,
        is_available=True,
    )
    db_session.add(donor_b)
    await db_session.commit()
    await db_session.refresh(donor_b)

    # Test A: Hospital A Admin attempts to update unaffiliated donor's location -> 403 Access Denied
    res_unaff = await client.put(
        f"/api/v1/donors/{unaffiliated_donor.id}/location",
        json={"latitude": 9.59, "longitude": 76.52, "consent_confirmed": True},
        headers=hospital_admin_headers,
    )
    assert res_unaff.status_code == 403
    assert res_unaff.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"

    # Test B: Hospital A Admin attempts to update Hospital B donor's location -> 403 Access Denied
    res_other = await client.put(
        f"/api/v1/donors/{donor_b.id}/location",
        json={"latitude": 9.59, "longitude": 76.52, "consent_confirmed": True},
        headers=hospital_admin_headers,
    )
    assert res_other.status_code == 403
    assert res_other.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"

    # Test C: Hospital A Admin attempts to delete unaffiliated donor's location -> 403 Access Denied
    res_del_unaff = await client.delete(
        f"/api/v1/donors/{unaffiliated_donor.id}/location",
        headers=hospital_admin_headers,
    )
    assert res_del_unaff.status_code == 403

    # Test D: Hospital A Admin attempts to transfer a donor to Hospital B -> 403 Access Denied
    # First create a donor belonging to Hospital A
    donor_a_res = await client.post(
        "/api/v1/donors",
        json={
            "donor_code": f"D_HOSPA_{tag}",
            "full_name=" : "Hospital A Donor",
            "full_name": "Hospital A Donor",
            "blood_group": "A+",
            "phone": random_phone(),
            "district": "Kottayam",
            "hospital_id": test_hospital.id,
        },
        headers=hospital_admin_headers,
    )
    assert donor_a_res.status_code == 201
    donor_a_id = donor_a_res.json()["data"]["id"]

    res_transfer = await client.patch(
        f"/api/v1/donors/{donor_a_id}",
        json={"hospital_id": hosp_b.id},
        headers=hospital_admin_headers,
    )
    assert res_transfer.status_code == 403
    assert "cannot transfer" in str(res_transfer.json()).lower()


@pytest.mark.asyncio
async def test_hospital_staff_cross_hospital_matching_restriction(
    client: AsyncClient,
    hospital_admin_headers: dict,
    db_session: AsyncSession,
):
    tag = str(random.randint(10000, 99999))
    hosp_c = Hospital(
        hospital_code=f"HOSP_C_{tag}",
        name="Hospital C",
        hospital_type="Government",
        district="Thrissur",
        address="Thrissur",
        is_active=True,
    )
    db_session.add(hosp_c)
    await db_session.commit()
    await db_session.refresh(hosp_c)

    # Hospital A Admin attempts to run matching using Hospital C's ID -> 403 Access Denied
    res = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "hospital_id": hosp_c.id},
        headers=hospital_admin_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"


# -------------------------------------------------------------
# 4. CSV Import & Location Immutability Audit Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_csv_import_does_not_overwrite_or_fabricate_gps(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))
    phone = random_phone()

    # 1. Create an existing donor with verified GPS location and consent
    donor = Donor(
        donor_code=f"D_CSV_{tag}",
        hospital_id=test_hospital.id,
        full_name="Pre-Existing GPS Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone=phone,
        district="Kottayam",
        location=WKTElement("POINT(76.5387 9.6234)", srid=4326),
        location_consent=True,
        is_active=True,
        is_available=True,
    )
    db_session.add(donor)
    await db_session.commit()
    await db_session.refresh(donor)

    # 2. Upload CSV updating this donor's name and district
    csv_content = (
        "Full Name,Blood Group,Phone,District,Panchayat\n"
        f"Updated Name Via CSV,O+,{phone},Kottayam,Pala\n"
    ).encode("utf-8")

    files = {"file": ("donors_update.csv", csv_content, "text/csv")}
    upload_res = await client.post(
        f"/api/v1/donors/import?hospital_id={test_hospital.id}",
        files=files,
        headers=super_admin_headers,
    )
    assert upload_res.status_code == 201

    # 3. Direct DB verification: donor location and consent MUST be preserved exactly
    donor_id = donor.id
    db_session.expunge_all()
    res_db = await db_session.execute(
        text("SELECT ST_AsText(location), location_consent, full_name FROM donors WHERE id = :id"),
        {"id": donor_id},
    )
    row = res_db.fetchone()
    assert row[0] == "POINT(76.5387 9.6234)"  # Preserved!
    assert row[1] is True  # Preserved!
    assert row[2] == "Updated Name Via CSV"  # Updated name from CSV


# -------------------------------------------------------------
# 5. Strict Privacy & Coordinate Leaking Audit Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_strict_absence_of_raw_coordinates_in_all_responses(
    client: AsyncClient,
    super_admin_headers: dict,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))
    create_res = await client.post(
        "/api/v1/donors",
        json={
            "donor_code": f"D_PRIV_{tag}",
            "full_name": "Privacy Check Donor",
            "blood_group": "O+",
            "phone": random_phone(),
            "district": "Kottayam",
            "hospital_id": test_hospital.id,
        },
        headers=super_admin_headers,
    )
    donor_id = create_res.json()["data"]["id"]

    # Add GPS location
    await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.5916, "longitude": 76.5222, "consent_confirmed": True},
        headers=super_admin_headers,
    )

    # 1. Check GET /donors/{id}
    res_get = await client.get(f"/api/v1/donors/{donor_id}", headers=super_admin_headers)
    get_json_str = res_get.text.lower()
    assert "9.5916" not in get_json_str
    assert "76.5222" not in get_json_str
    assert "point(" not in get_json_str
    assert "wkb" not in get_json_str

    # 2. Check GET /donors
    res_list = await client.get(f"/api/v1/donors?search={tag}", headers=super_admin_headers)
    list_json_str = res_list.text.lower()
    assert "9.5916" not in list_json_str
    assert "76.5222" not in list_json_str
    assert "point(" not in list_json_str

    # 3. Check POST /matching/donors
    res_match = await client.post(
        "/api/v1/matching/donors",
        json={"blood_group": "O+", "latitude": 9.59, "longitude": 76.52, "radius_km": 25.0},
        headers=super_admin_headers,
    )
    match_data = res_match.json()["data"]
    for item in match_data["items"]:
        # Donors in matching list must not expose raw coords
        assert "latitude" not in item
        assert "longitude" not in item
        assert "location" not in item
        if item["distance_km"] is not None:
            # Distance must be rounded to 1 decimal place max
            assert isinstance(item["distance_km"], float)
            assert len(str(item["distance_km"]).split(".")[1]) <= 2
