import io
import time
import openpyxl
import pytest
from httpx import AsyncClient
from app.models.hospital import Hospital
from app.models.user import User


def create_sample_csv(rows: list, headers: list = None) -> bytes:
    if headers is None:
        headers = ["full_name", "blood_group", "phone", "email", "gender", "district", "panchayat", "address", "is_available"]
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(val) for val in r))
    return "\n".join(lines).encode("utf-8")


def create_sample_xlsx(rows: list, headers: list = None) -> bytes:
    if headers is None:
        headers = ["full_name", "blood_group", "phone", "email", "gender", "district", "panchayat", "address", "is_available"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()


import random


def random_phone() -> str:
    return f"9{random.randint(100000000, 999999999)}"


@pytest.mark.asyncio
async def test_preview_donor_import_csv(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    p1 = random_phone()
    p2 = random_phone()

    csv_data = create_sample_csv([
        ["Preview User 1", "O+", p1, "p1@example.com", "Male", "Kottayam", "Pala", "Address 1", "true"],
        ["Preview User 2", "AB-", p2, "p2@example.com", "Female", "Ernakulam", "Kochi", "Address 2", "yes"],
        ["Invalid User", "X+", "12345", "bademail", "Other", "Kottayam", "Pala", "Address 3", "true"],
    ])

    files = {"file": ("donors_preview.csv", csv_data, "text/csv")}
    response = await client.post(
        "/api/v1/donors/import/preview",
        files=files,
        data={"hospital_id": test_hospital.id},
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    res_data = data["data"]
    assert res_data["total_rows"] == 3
    assert res_data["valid_rows"] == 2
    assert res_data["invalid_rows"] == 1
    assert res_data["new_donors"] == 2
    assert len(res_data["errors"]) == 1
    assert res_data["errors"][0]["row"] == 4  # Row 4 in sheet
    assert len(res_data["preview_rows"]) == 3

    # Ensure preview didn't write to DB (searching for phone returns empty)
    check_res = await client.get(f"/api/v1/donors?search={p1}", headers=super_admin_headers)
    assert check_res.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_execute_donor_import_csv_success(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    p1 = random_phone()
    p2 = random_phone()

    csv_data = create_sample_csv([
        ["Alice Thomas", "A+", p1, "alice@example.com", "Female", "Kottayam", "Ettumanoor", "House 10", "true"],
        ["Bob Joseph", "B-", p2, "bob@example.com", "Male", "Kottayam", "Pala", "House 20", "false"],
    ])

    files = {"file": ("donors_import.csv", csv_data, "text/csv")}
    response = await client.post(
        "/api/v1/donors/import",
        files=files,
        data={"hospital_id": test_hospital.id},
        headers=super_admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    res_data = data["data"]
    assert res_data["total_records"] == 2
    assert res_data["successful_records"] == 2
    assert res_data["failed_records"] == 0
    assert res_data["new_donors_created"] == 2
    assert res_data["batch"]["status"] == "COMPLETED"

    # Verify donors can be queried from API
    q_res = await client.get(f"/api/v1/donors?search={p1}", headers=super_admin_headers)
    assert q_res.status_code == 200
    donor_items = q_res.json()["data"]["items"]
    assert len(donor_items) == 1
    assert donor_items[0]["full_name"] == "Alice Thomas"
    assert donor_items[0]["phone"] == f"+91{p1}"
    assert donor_items[0]["blood_group"] == "A+"
    assert donor_items[0]["is_available"] is True


@pytest.mark.asyncio
async def test_import_existing_donor_update_strategy(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    phone = random_phone()

    # 1. Create donor via single API
    init_res = await client.post(
        "/api/v1/donors",
        json={
            "full_name": "Original Name",
            "blood_group": "O+",
            "phone": phone,
            "district": "Kottayam",
            "panchayat": "Old Panchayat",
            "is_available": True,
        },
        headers=super_admin_headers,
    )
    assert init_res.status_code == 201
    orig_donor = init_res.json()["data"]
    orig_code = orig_donor["donor_code"]

    # 2. Import CSV with same phone, updated name, address, but empty panchayat
    csv_data = create_sample_csv([
        ["Updated Name", "O+", phone, "updated@example.com", "Male", "Kottayam", "", "New Street Address", "false"],
    ])

    files = {"file": ("donor_update.csv", csv_data, "text/csv")}
    imp_res = await client.post(
        "/api/v1/donors/import",
        files=files,
        data={"hospital_id": test_hospital.id},
        headers=super_admin_headers,
    )
    assert imp_res.status_code == 201
    imp_data = imp_res.json()["data"]
    assert imp_data["successful_records"] == 1
    assert imp_data["new_donors_created"] == 0
    assert imp_data["existing_donors_updated"] == 1

    # 3. Retrieve donor and check fields
    donor_res = await client.get(f"/api/v1/donors/{orig_donor['id']}", headers=super_admin_headers)
    updated_donor = donor_res.json()["data"]
    assert updated_donor["donor_code"] == orig_code  # Identity preserved
    assert updated_donor["full_name"] == "Updated Name"  # Updated
    assert updated_donor["email"] == "updated@example.com"  # Updated
    assert updated_donor["address"] == "New Street Address"  # Updated
    assert updated_donor["panchayat"] == "Old Panchayat"  # Blank didn't overwrite!
    assert updated_donor["is_available"] is False  # Updated availability


@pytest.mark.asyncio
async def test_execute_donor_import_xlsx_success(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    p1 = random_phone()
    p2 = random_phone()

    xlsx_data = create_sample_xlsx([
        ["Excel Donor 1", "AB+", int(p1), "excel1@example.com", "Male", "Ernakulam", "Aluva", "Aluva Road", True],
        ["Excel Donor 2", "O-", p2, "excel2@example.com", "Female", "Kottayam", "Changanassery", "Main St", 0],
    ])

    files = {"file": ("donors_excel.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = await client.post(
        "/api/v1/donors/import",
        files=files,
        data={"hospital_id": test_hospital.id},
        headers=super_admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    res_data = data["data"]
    assert res_data["total_records"] == 2
    assert res_data["successful_records"] == 2
    assert res_data["failed_records"] == 0
    assert res_data["new_donors_created"] == 2

    # Verify donor with integer phone was correctly normalized
    q_res = await client.get(f"/api/v1/donors?search={p1}", headers=super_admin_headers)
    assert q_res.status_code == 200
    items = q_res.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["phone"] == f"+91{p1}"
    assert items[0]["blood_group"] == "AB+"


@pytest.mark.asyncio
async def test_import_batches_list_and_detail(
    client: AsyncClient, super_admin_headers: dict, test_hospital: Hospital
):
    # 1. List batches
    res = await client.get("/api/v1/donors/imports", headers=super_admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    batches = data["data"]["items"]
    assert len(batches) >= 1

    latest_batch_id = batches[0]["id"]

    # 2. Get batch detail
    detail_res = await client.get(f"/api/v1/donors/imports/{latest_batch_id}", headers=super_admin_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == latest_batch_id


@pytest.mark.asyncio
async def test_hospital_admin_scoping_on_import(
    client: AsyncClient, hospital_admin_headers: dict, test_hospital: Hospital
):
    ts = str(int(time.time() * 1000))[-7:]
    p1 = f"94{ts}11"

    csv_data = create_sample_csv([
        ["Hosp Admin Donor", "B+", p1, "hosp@example.com", "Male", "Kottayam", "Pala", "Hospital Staff St", "true"],
    ])

    # Attempt to import with a different/fake hospital_id -> Forbidden
    files = {"file": ("unauthorized.csv", csv_data, "text/csv")}
    forbidden_res = await client.post(
        "/api/v1/donors/import",
        files=files,
        data={"hospital_id": 999999},
        headers=hospital_admin_headers,
    )
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "HOSPITAL_ACCESS_DENIED"

    # Import without explicit hospital_id -> automatically scoped to hospital_admin's hospital
    files2 = {"file": ("authorized.csv", csv_data, "text/csv")}
    ok_res = await client.post(
        "/api/v1/donors/import",
        files=files2,
        headers=hospital_admin_headers,
    )
    assert ok_res.status_code == 201
    assert ok_res.json()["data"]["batch"]["hospital_id"] == test_hospital.id


@pytest.mark.asyncio
async def test_invalid_file_format_and_empty_file(
    client: AsyncClient, super_admin_headers: dict
):
    # Test invalid extension (.pdf)
    files = {"file": ("test.pdf", b"%PDF-1.4 mock content", "application/pdf")}
    res = await client.post("/api/v1/donors/import", files=files, headers=super_admin_headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    # Test empty CSV
    files_empty = {"file": ("empty.csv", b"", "text/csv")}
    res_empty = await client.post("/api/v1/donors/import", files=files_empty, headers=super_admin_headers)
    assert res_empty.status_code == 422
    assert res_empty.json()["error"]["code"] == "VALIDATION_ERROR"
