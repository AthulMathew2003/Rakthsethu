import pytest
from app.core.exceptions import ValidationException
from app.core.location_service import (
    KERALA_DISTRICTS,
    get_districts,
    get_local_bodies,
    validate_district_and_panchayat,
)


def test_all_14_kerala_districts_available():
    districts = get_districts()
    assert len(districts) == 14
    expected = [
        "Alappuzha",
        "Ernakulam",
        "Idukki",
        "Kannur",
        "Kasaragod",
        "Kollam",
        "Kottayam",
        "Kozhikode",
        "Malappuram",
        "Palakkad",
        "Pathanamthitta",
        "Thiruvananthapuram",
        "Thrissur",
        "Wayanad",
    ]
    assert districts == expected


@pytest.mark.parametrize("district", KERALA_DISTRICTS)
def test_each_district_returns_only_its_associated_local_bodies(district: str):
    local_bodies = get_local_bodies(district)
    assert len(local_bodies) > 0, f"District {district} should have local bodies"

    names = [lb["name"] for lb in local_bodies]
    types = {lb["type"] for lb in local_bodies}

    # Verify each item has required keys
    for lb in local_bodies:
        assert "code" in lb
        assert "name" in lb
        assert "type" in lb

    # Verify no local bodies from other districts leak in
    if district == "Kottayam":
        assert "Kumarakom" in names
        assert "Pala" in names or "Palai" in names
        assert "Aluva" not in names  # Aluva is in Ernakulam
    elif district == "Ernakulam":
        assert "Aluva" in names
        assert "Kochi" in names
        assert "Kumarakom" not in names  # Kumarakom is in Kottayam


def test_invalid_district_rejected():
    with pytest.raises(ValidationException) as exc_info:
        get_local_bodies("Delhi")
    assert "not a valid Kerala district" in str(exc_info.value.message)


def test_search_local_bodies():
    results = get_local_bodies("Ernakulam", search="aluva")
    assert len(results) >= 1
    assert any(lb["name"] == "Aluva" for lb in results)

    # Empty search match
    no_results = get_local_bodies("Ernakulam", search="nonexistentxyz")
    assert len(no_results) == 0


def test_validate_valid_district_and_panchayat():
    dist, p = validate_district_and_panchayat("Kottayam", "Kumarakom")
    assert dist == "Kottayam"
    assert p == "Kumarakom"

    dist, p = validate_district_and_panchayat("Ernakulam", "Aluva")
    assert dist == "Ernakulam"
    assert p == "Aluva"


def test_validate_case_insensitive_and_aliases():
    # Lowercase district and alias "Kochi Corporation"
    dist, p = validate_district_and_panchayat("ernakulam", "kochi corporation")
    assert dist == "Ernakulam"
    assert p == "Kochi"

    # Pala alias in Kottayam
    dist, p = validate_district_and_panchayat("KOTTAYAM", "pala")
    assert dist == "Kottayam"
    assert p == "Pala"


def test_validate_mismatched_district_panchayat_rejected():
    # Aluva belongs to Ernakulam, not Kottayam
    with pytest.raises(ValidationException) as exc_info:
        validate_district_and_panchayat("Kottayam", "Aluva")
    assert "belongs to district 'Ernakulam', not 'Kottayam'" in str(exc_info.value.message)

    # Kumarakom belongs to Kottayam, not Kozhikode
    with pytest.raises(ValidationException) as exc_info:
        validate_district_and_panchayat("Kozhikode", "Kumarakom")
    assert "belongs to district 'Kottayam', not 'Kozhikode'" in str(exc_info.value.message)


def test_validate_unknown_panchayat_rejected():
    with pytest.raises(ValidationException) as exc_info:
        validate_district_and_panchayat("Kottayam", "RandomFictionalPlace")
    assert "is not a recognized local body in district 'Kottayam'" in str(exc_info.value.message)


def test_backward_compatibility_empty_panchayat():
    # When panchayat is omitted or None, existing donor records must not fail
    dist, p = validate_district_and_panchayat("Kottayam", None)
    assert dist == "Kottayam"
    assert p is None

    dist, p = validate_district_and_panchayat("Ernakulam", "")
    assert dist == "Ernakulam"
    assert p is None


@pytest.mark.asyncio
async def test_locations_api_endpoints():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Districts endpoint
        res = await ac.get("/api/v1/locations/districts")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert len(body["data"]) == 14
        assert "Ernakulam" in body["data"]
        assert "Kottayam" in body["data"]

        # 2. Local bodies endpoint for valid district
        res_lbs = await ac.get("/api/v1/locations/local-bodies?district=Kottayam")
        assert res_lbs.status_code == 200
        body_lbs = res_lbs.json()
        assert body_lbs["success"] is True
        assert len(body_lbs["data"]) > 0
        names = [item["name"] for item in body_lbs["data"]]
        assert "Kumarakom" in names

        # 3. Local bodies endpoint with search
        res_search = await ac.get("/api/v1/locations/local-bodies?district=Ernakulam&search=aluva")
        assert res_search.status_code == 200
        body_search = res_search.json()
        assert body_search["success"] is True
        assert any(item["name"] == "Aluva" for item in body_search["data"])

        # 4. Local bodies endpoint with invalid district
        res_invalid = await ac.get("/api/v1/locations/local-bodies?district=InvalidDistrict")
        assert res_invalid.status_code == 422
        body_invalid = res_invalid.json()
        assert body_invalid["success"] is False


@pytest.mark.asyncio
async def test_donor_service_location_validation():
    from unittest.mock import AsyncMock, MagicMock
    from app.schemas.donor import DonorCreate, DonorUpdate
    from app.services.donor_service import DonorService

    session = AsyncMock()
    service = DonorService(session)
    service.donor_repo = MagicMock()
    service.donor_repo.get_by_phone = AsyncMock(return_value=None)
    service.donor_repo.get_by_code = AsyncMock(return_value=None)
    service.donor_repo.generate_next_donor_code = AsyncMock(return_value="DNR-TEST-001")
    service.donor_repo.add = AsyncMock()

    # 1. Invalid district & panchayat combination is rejected
    invalid_create = DonorCreate(
        full_name="Tester",
        blood_group="O+",
        phone="+919876543210",
        district="Kottayam",
        panchayat="Aluva",  # Aluva is in Ernakulam
        is_available=True,
    )
    with pytest.raises(ValidationException) as exc:
        await service.create_donor(invalid_create)
    assert "belongs to district 'Ernakulam', not 'Kottayam'" in str(exc.value.message)

    # 2. Valid district & panchayat combination succeeds
    valid_create = DonorCreate(
        full_name="Tester",
        blood_group="O+",
        phone="+919876543210",
        district="Kottayam",
        panchayat="Kumarakom",
        is_available=True,
    )
    # mock refresh
    async def fake_refresh(obj):
        from datetime import datetime, timezone
        obj.id = 1
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
    session.refresh.side_effect = fake_refresh

    result = await service.create_donor(valid_create)
    assert result.district == "Kottayam"
    assert result.panchayat == "Kumarakom"

    # 3. Backward compatibility: empty panchayat succeeds
    legacy_create = DonorCreate(
        full_name="Legacy Donor",
        blood_group="A+",
        phone="+919876543211",
        district="Ernakulam",
        panchayat=None,
        is_available=True,
    )
    result_legacy = await service.create_donor(legacy_create)
    assert result_legacy.district == "Ernakulam"
    assert result_legacy.panchayat is None

    # 4. update_donor rejects invalid panchayat for existing donor's district
    fake_donor = MagicMock()
    fake_donor.id = 1
    fake_donor.phone = "+919876543210"
    fake_donor.district = "Kottayam"
    fake_donor.panchayat = "Kumarakom"
    fake_donor.location = None
    fake_donor.location_consent = False
    fake_donor.location_consent_recorded_at = None
    service.donor_repo.get_by_id = AsyncMock(return_value=fake_donor)

    with pytest.raises(ValidationException):
        await service.update_donor(1, DonorUpdate(panchayat="Aluva"))

