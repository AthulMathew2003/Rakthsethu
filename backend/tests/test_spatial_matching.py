from datetime import date, timedelta
import random
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.enums import BloodGroup, DonationStatus
from app.models.hospital import Hospital


def random_phone() -> str:
    return f"9{random.randint(100000000, 999999999)}"


# -------------------------------------------------------------
# 1. Schema & Migration Verification Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_spatial_columns_and_gist_indexes_exist(db_session: AsyncSession):
    # Verify donors.location column is geography
    res_col = await db_session.execute(text("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'donors' AND column_name = 'location';
    """))
    donor_col = res_col.fetchone()
    assert donor_col is not None
    assert donor_col[2] == "geography"

    # Verify hospitals.location column is geography
    res_hosp_col = await db_session.execute(text("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = 'hospitals' AND column_name = 'location';
    """))
    hosp_col = res_hosp_col.fetchone()
    assert hosp_col is not None
    assert hosp_col[2] == "geography"

    # Verify GiST indexes exist
    res_idx = await db_session.execute(text("""
        SELECT indexname, indexdef FROM pg_indexes 
        WHERE indexname IN ('idx_donors_location_gist', 'idx_hospitals_location_gist');
    """))
    indexes = {row[0]: row[1] for row in res_idx.fetchall()}
    assert "idx_donors_location_gist" in indexes
    assert "gist (location)" in indexes["idx_donors_location_gist"].lower()
    assert "idx_hospitals_location_gist" in indexes
    assert "gist (location)" in indexes["idx_hospitals_location_gist"].lower()


@pytest.mark.asyncio
async def test_existing_hospitals_coordinate_backfill(db_session: AsyncSession):
    # Verify hospitals with lat/long have populated spatial location
    res = await db_session.execute(text("""
        SELECT id, name, latitude, longitude, ST_AsText(location)
        FROM hospitals
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
    """))
    hospitals = res.fetchall()
    assert len(hospitals) >= 8
    for h in hospitals:
        lat, lon, wkt = h[2], h[3], h[4]
        assert wkt is not None
        assert wkt.startswith("POINT(")
        # PostGIS WKT represents longitude as X, latitude as Y
        expected_prefix = f"POINT({lon} {lat})"
        assert wkt == expected_prefix


# -------------------------------------------------------------
# 2. Donor Location Default & Lifecycle Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_donor_location_default_null_and_privacy(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))
    payload = {
        "donor_code": f"D_NULL_{tag}",
        "full_name": "Test Default Null Location Donor",
        "blood_group": "O+",
        "phone": random_phone(),
        "district": "Kottayam",
        "hospital_id": test_hospital.id,
    }

    # Register donor without coordinates
    res = await client.post("/api/v1/donors", json=payload, headers=super_admin_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["has_location"] is False
    assert "latitude" not in data
    assert "longitude" not in data
    assert "location" not in data
    donor_id = data["id"]

    # Verify DB directly: location is NULL
    res_db = await db_session.execute(
        text("SELECT location FROM donors WHERE id = :donor_id"),
        {"donor_id": donor_id},
    )
    assert res_db.scalar_one_or_none() is None

    # Retrieve donor: check absence of raw coordinates in API response
    get_res = await client.get(f"/api/v1/donors/{donor_id}", headers=super_admin_headers)
    assert get_res.status_code == 200
    get_data = get_res.json()["data"]
    assert get_data["has_location"] is False
    assert "latitude" not in get_data
    assert "longitude" not in get_data
    assert "location" not in get_data


@pytest.mark.asyncio
async def test_donor_location_update_and_removal(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    tag = str(random.randint(10000, 99999))
    payload = {
        "donor_code": f"D_LOC_{tag}",
        "full_name": "Test GPS Lifecycle Donor",
        "blood_group": "A+",
        "phone": random_phone(),
        "district": "Kottayam",
        "hospital_id": test_hospital.id,
    }
    create_res = await client.post("/api/v1/donors", json=payload, headers=super_admin_headers)
    donor_id = create_res.json()["data"]["id"]

    # 1. Invalid coordinate validation [-90, 90] and [-180, 180]
    res_bad_lat = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 95.0, "longitude": 76.5, "consent_confirmed": True},
        headers=super_admin_headers,
    )
    assert res_bad_lat.status_code == 422

    res_bad_lon = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.5, "longitude": 185.0, "consent_confirmed": True},
        headers=super_admin_headers,
    )
    assert res_bad_lon.status_code == 422

    # 2. Update location with valid coordinates and consent (Kottayam)
    res_update = await client.put(
        f"/api/v1/donors/{donor_id}/location",
        json={"latitude": 9.5916, "longitude": 76.5222, "consent_confirmed": True},
        headers=super_admin_headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["data"]["has_location"] is True
    assert res_update.json()["data"]["location_consent"] is True

    # Direct DB verification: check ST_AsText and location_consent
    res_db = await db_session.execute(
        text("SELECT ST_AsText(location), location_consent FROM donors WHERE id = :donor_id"),
        {"donor_id": donor_id},
    )
    row_db = res_db.fetchone()
    assert row_db[0] == "POINT(76.5222 9.5916)"
    assert row_db[1] is True

    # 3. Remove location via DELETE endpoint
    res_del = await client.delete(f"/api/v1/donors/{donor_id}/location", headers=super_admin_headers)
    assert res_del.status_code == 200
    assert res_del.json()["data"]["has_location"] is False
    assert res_del.json()["data"]["location_consent"] is False

    res_db_after = await db_session.execute(
        text("SELECT location, location_consent FROM donors WHERE id = :donor_id"),
        {"donor_id": donor_id},
    )
    row_after = res_db_after.fetchone()
    assert row_after[0] is None
    assert row_after[1] is False


@pytest.mark.asyncio
async def test_unauthorized_location_update(client: AsyncClient):
    # Attempting to update donor location without token -> 401
    res = await client.put(
        "/api/v1/donors/1/location",
        json={"latitude": 9.59, "longitude": 76.52, "consent_confirmed": True},
    )
    assert res.status_code == 401


# -------------------------------------------------------------
# 3. Distance-Based Matching & Ranking Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_spatial_distance_matching_ranking_and_boundaries(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
    test_hospital: Hospital,
):
    today = date.today()
    tag = str(random.randint(10000, 99999))

    # Origin: Kottayam Center (lat: 9.5916, lon: 76.5222)
    # Donor Near: ~2 km away (lat: 9.60, lon: 76.53)
    d_near = Donor(
        donor_code=f"D_NEAR_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Near (2km)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Kottayam East",
        location=WKTElement("POINT(76.53 9.60)", srid=4326),
        location_consent=True,
        is_active=True,
        is_available=True,
    )

    # Donor Mid: ~15 km away (lat: 9.70, lon: 76.55)
    d_mid = Donor(
        donor_code=f"D_MID_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Mid (15km)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        location=WKTElement("POINT(76.55 9.70)", srid=4326),
        location_consent=True,
        is_active=True,
        is_available=True,
    )

    # Donor Far: ~60 km away in Kochi (lat: 9.98, lon: 76.28) -> outside 25km radius
    d_far = Donor(
        donor_code=f"D_FAR_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Far (60km)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Ernakulam",
        panchayat="Kochi",
        location=WKTElement("POINT(76.28 9.98)", srid=4326),
        location_consent=True,
        is_active=True,
        is_available=True,
    )

    # Donor Fallback: In Kottayam with NO GPS coordinates
    d_fallback = Donor(
        donor_code=f"D_FB_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Fallback (No GPS)",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        panchayat="Pala",
        location=None,
        location_consent=False,
        is_active=True,
        is_available=True,
    )

    # Donor Ineligible: Near (~2 km), but cooldown active (donated 10 days ago)
    d_cooldown = Donor(
        donor_code=f"D_COOL_{tag}",
        hospital_id=test_hospital.id,
        full_name="Donor Ineligible Cooldown",
        blood_group=BloodGroup.O_POSITIVE,
        phone=random_phone(),
        district="Kottayam",
        location=WKTElement("POINT(76.53 9.60)", srid=4326),
        location_consent=True,
        is_active=True,
        is_available=True,
    )

    db_session.add_all([d_near, d_mid, d_far, d_fallback, d_cooldown])
    await db_session.commit()
    for d in [d_near, d_mid, d_far, d_fallback, d_cooldown]:
        await db_session.refresh(d)

    # Add completed donation for cooldown donor
    don_cool = Donation(
        donation_code=f"DON_C_{tag}",
        donor_id=d_cooldown.id,
        hospital_id=test_hospital.id,
        donation_date=today - timedelta(days=10),
        status=DonationStatus.COMPLETED,
        units_donated=1,
    )
    db_session.add(don_cool)
    await db_session.commit()

    # Query matching using explicit origin coordinates (lat: 9.5916, lon: 76.5222, radius: 25 km)
    match_payload = {
        "blood_group": "O+",
        "district": "Kottayam",
        "latitude": 9.5916,
        "longitude": 76.5222,
        "radius_km": 25.0,
        "include_fallback": True,
        "hospital_id": test_hospital.id,
        "limit": 100,
    }
    res = await client.post("/api/v1/matching/donors", json=match_payload, headers=super_admin_headers)
    assert res.status_code == 200
    res_data = res.json()["data"]

    assert res_data["origin_type"] == "EXPLICIT_GPS"
    assert res_data["radius_km"] == 25.0

    items = res_data["items"]
    matched_ids = [item["donor_id"] for item in items]

    # 1. d_near and d_mid must be present
    assert d_near.id in matched_ids
    assert d_mid.id in matched_ids

    # 2. d_far (> 25km) and d_cooldown (ineligible) must NOT be present
    assert d_far.id not in matched_ids
    assert d_cooldown.id not in matched_ids

    # 3. Distance ranking: d_near must appear BEFORE d_mid
    pos_near = matched_ids.index(d_near.id)
    pos_mid = matched_ids.index(d_mid.id)
    assert pos_near < pos_mid

    near_item = next(it for it in items if it["donor_id"] == d_near.id)
    mid_item = next(it for it in items if it["donor_id"] == d_mid.id)
    assert near_item["distance_km"] is not None
    assert mid_item["distance_km"] is not None
    assert near_item["distance_km"] < mid_item["distance_km"]
    assert near_item["match_category"] == "PROXIMITY"
    assert "Proximity match" in near_item["match_reason"]

    # 4. Coordinate-less fallback candidate: distance is null, ranked in Tier 2 (after all proximity items)
    assert d_fallback.id in matched_ids
    pos_fallback = matched_ids.index(d_fallback.id)
    assert pos_fallback > pos_near
    assert pos_fallback > pos_mid

    fb_item = next(it for it in items if it["donor_id"] == d_fallback.id)
    assert fb_item["distance_km"] is None
    assert fb_item["match_category"] == "FALLBACK_DISTRICT"
    assert "District fallback (No GPS coordinates registered)" in fb_item["match_reason"]


@pytest.mark.asyncio
async def test_hospital_origin_spatial_matching(
    client: AsyncClient,
    super_admin_headers: dict,
    db_session: AsyncSession,
):
    # Test origin derived from a hospital's verified coordinates
    # Select Government Medical College Kottayam (id 46, coords: 9.6234, 76.5387)
    res_hosp = await db_session.execute(text("""
        SELECT id, name, latitude, longitude FROM hospitals 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL 
        LIMIT 1;
    """))
    hosp = res_hosp.fetchone()
    assert hosp is not None
    hosp_id = hosp[0]

    match_payload = {
        "blood_group": "O+",
        "hospital_id": hosp_id,
        "radius_km": 50.0,
    }
    res = await client.post("/api/v1/matching/donors", json=match_payload, headers=super_admin_headers)
    assert res.status_code == 200
    res_data = res.json()["data"]
    assert res_data["origin_type"] == "HOSPITAL_LOCATION"
    assert res_data["origin_latitude"] == hosp[2]
    assert res_data["origin_longitude"] == hosp[3]
    assert res_data["radius_km"] == 50.0


@pytest.mark.asyncio
async def test_legacy_district_matching_when_no_coordinates(
    client: AsyncClient,
    super_admin_headers: dict,
):
    # Backward compatibility: matching with only district specified
    match_payload = {
        "blood_group": "O+",
        "district": "Kottayam",
    }
    res = await client.post("/api/v1/matching/donors", json=match_payload, headers=super_admin_headers)
    assert res.status_code == 200
    res_data = res.json()["data"]
    assert res_data["origin_type"] == "DISTRICT_DEFAULT"
    assert res_data["origin_latitude"] is None
    assert res_data["origin_longitude"] is None
    assert res_data["radius_km"] is None
    for item in res_data["items"]:
        assert item["distance_km"] is None
        assert item["match_category"] == "DISTRICT_DEFAULT"
