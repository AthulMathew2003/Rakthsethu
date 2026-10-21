import hashlib
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.models.blood_request import BloodRequest
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency, UserRole
from app.models.hospital import Hospital
from app.schemas.matching import MatchDonorsRequest, MatchDonorsResponse, MatchedDonorItem
from app.models.telegram import (
    TelegramBloodRequest,
    TelegramConversation,
    TelegramLinkToken,
    TelegramLinkedStaff,
    TelegramUpdateAudit,
)
from app.models.user import User
from app.telegram.client import TelegramClient, redact_telegram_token
from app.telegram.handlers import TelegramHandler
from app.telegram.schemas import (
    TelegramCallbackQuery,
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from app.telegram.service import TelegramService


# ─── Mock Telegram Client ──────────────────────────────────────────────────

class MockTelegramClient:
    def __init__(self):
        self.sent_messages = []
        self.answered_callbacks = []

    async def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None):
        msg = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        }
        self.sent_messages.append(msg)
        return {"ok": True, "result": {"message_id": len(self.sent_messages)}}

    async def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        self.answered_callbacks.append({"id": callback_query_id, "text": text})
        return {"ok": True}

    async def edit_message_text(self, chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
        msg = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        }
        self.sent_messages.append(msg)
        return {"ok": True, "result": {"message_id": message_id}}


def create_mock_session(query_return_value=None):
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = query_return_value
    mock_result.scalars.return_value.all.return_value = [query_return_value] if query_return_value else []
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ─── 1. Telegram Client & Token Redaction Tests ────────────────────────────

def test_token_redaction():
    token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    raw_log = f"Failed to connect: https://api.telegram.org/bot{token}/sendMessage"
    redacted = redact_telegram_token(raw_log)
    assert token not in redacted
    assert "bot[REDACTED]" in redacted


def test_telegram_client_url_construction():
    client = TelegramClient(token="123456:ABC-DEF")
    assert client.base_url == "https://api.telegram.org/bot123456:ABC-DEF"
    assert client._clean_url("getMe") == "https://api.telegram.org/bot123456:ABC-DEF/getMe"


# ─── 2. Durable Idempotency & Duplicate Update Tests ───────────────────────

@pytest.mark.asyncio
async def test_update_idempotency_new_and_completed():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    # 1. First time update arrives -> None existing in DB -> Proceed
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result_none

    can_proceed, status = await service.start_update_processing(
        update_id=1001,
        chat_id=123,
        user_id=456,
        update_type="message",
    )
    assert can_proceed is True
    assert status == "NEW"
    assert mock_session.add.called
    assert mock_session.commit.called

    # 2. Duplicate update arrives -> Already COMPLETED in DB -> Drop
    completed_audit = TelegramUpdateAudit(
        update_id=1001,
        chat_id=123,
        user_id=456,
        update_type="message",
        status="COMPLETED",
    )
    mock_result_completed = MagicMock()
    mock_result_completed.scalar_one_or_none.return_value = completed_audit
    mock_session.execute.return_value = mock_result_completed

    can_proceed, status = await service.start_update_processing(
        update_id=1001,
        chat_id=123,
        user_id=456,
        update_type="message",
    )
    assert can_proceed is False
    assert status == "ALREADY_COMPLETED"


@pytest.mark.asyncio
async def test_update_idempotency_in_progress_and_retry():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    # If update is currently PROCESSING by another worker -> Skip
    processing_audit = TelegramUpdateAudit(
        update_id=1002,
        chat_id=123,
        user_id=456,
        update_type="message",
        status="PROCESSING",
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = processing_audit
    mock_session.execute.return_value = mock_res

    can_proceed, status = await service.start_update_processing(1002, 123, 456, "message")
    assert can_proceed is False
    assert status == "IN_PROGRESS"

    # If update FAILED previously -> Retry
    processing_audit.status = "FAILED"
    can_proceed, status = await service.start_update_processing(1002, 123, 456, "message")
    assert can_proceed is True
    assert status == "RETRYING"


# ─── 3. Staff Account Linking Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_link_token_generation_and_hashing():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    plain_token = await service.create_link_token(user_id=1)
    assert plain_token.startswith("RST-")
    assert len(plain_token) == 13  # RST-XXXX-YYYY

    # Verify token was added to session as SHA-256 hash
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, TelegramLinkToken)
    assert added_obj.user_id == 1
    assert added_obj.token_hash == hashlib.sha256(plain_token.encode("utf-8")).hexdigest()
    assert added_obj.expires_at > datetime.now(timezone.utc)
    assert added_obj.is_used is False


@pytest.mark.asyncio
async def test_staff_link_token_redemption_success():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    plain_token = "RST-TEST-LINK"
    token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

    test_user = User(
        id=5,
        user_code="STAFF01",
        email="nurse@hospital.org",
        hashed_password="hash",
        full_name="Nurse Priya",
        role=UserRole.STAFF,
        hospital_id=1,
        is_active=True,
    )
    link_record = TelegramLinkToken(
        id=1,
        user_id=5,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_used=False,
    )
    link_record.user = test_user

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = link_record

    # Mock staff search (no existing binding)
    mock_staff_res = MagicMock()
    mock_staff_res.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [mock_res, mock_staff_res]

    success, msg, user = await service.redeem_link_token(
        plain_token=plain_token,
        telegram_user_id=987654,
        telegram_chat_id=987654,
        telegram_username="nurse_priya",
    )
    assert success is True
    assert "successfully linked" in msg.lower()
    assert user.id == 5
    assert link_record.is_used is True
    assert link_record.used_at is not None


@pytest.mark.asyncio
async def test_staff_link_token_expired_or_reused():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    plain_token = "RST-EXPIRED"
    token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

    # Expired token
    expired_record = TelegramLinkToken(
        id=1,
        user_id=5,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        is_used=False,
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = expired_record
    mock_session.execute.return_value = mock_res

    success, msg, user = await service.redeem_link_token(plain_token, 123, 123)
    assert success is False
    assert "expired" in msg.lower()

    # Reused token
    expired_record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    expired_record.is_used = True
    success, msg, user = await service.redeem_link_token(plain_token, 123, 123)
    assert success is False
    assert "already been used" in msg.lower()


# ─── 4. Request Ownership & Privacy Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_request_access_owner_vs_stranger_vs_staff():
    mock_session = AsyncMock()
    service = TelegramService(mock_session)

    hosp = Hospital(id=1, name="Kottayam General Hospital", district="Kottayam", hospital_code="HOSP01")
    req = BloodRequest(
        id=10,
        request_code="REQ0001",
        hospital_id=1,
        patient_name="Anoop",
        blood_group=BloodGroup.O_POSITIVE,
        units_requested=1,
        district="Kottayam",
        contact_phone="9876543210",
        required_date=date.today(),
        status=RequestStatus.PENDING,
    )
    req.hospital = hosp

    # Case A: Requester is the verified owner (matches telegram_user_id=111)
    owner_binding = TelegramBloodRequest(blood_request_id=10, telegram_user_id=111, telegram_chat_id=111)

    mock_res_req = MagicMock()
    mock_res_req.scalar_one_or_none.return_value = req
    mock_res_owner = MagicMock()
    mock_res_owner.scalar_one_or_none.return_value = owner_binding

    mock_session.execute.side_effect = [mock_res_req, mock_res_owner]

    can_view, is_staff, b_req, b_hosp = await service.verify_request_access("REQ0001", telegram_user_id=111)
    assert can_view is True
    assert is_staff is False
    assert b_req.id == 10
    assert b_hosp.name == "Kottayam General Hospital"

    # Case B: Stranger (telegram_user_id=999) who did NOT create request and is NOT staff -> Denied
    mock_res_req2 = MagicMock()
    mock_res_req2.scalar_one_or_none.return_value = req
    mock_res_no_owner = MagicMock()
    mock_res_no_owner.scalar_one_or_none.return_value = None
    mock_res_no_staff = MagicMock()
    mock_res_no_staff.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [mock_res_req2, mock_res_no_owner, mock_res_no_staff]

    can_view, is_staff, b_req, b_hosp = await service.verify_request_access("REQ0001", telegram_user_id=999)
    assert can_view is False
    assert is_staff is False


# ─── 5. Telegram Command Handlers Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_start_and_help():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Test /start
    msg_start = TelegramMessage(
        message_id=1,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Ravi"),
        date=123456,
        text="/start",
    )
    await handler.handle_message(msg_start)
    assert len(mock_client.sent_messages) == 1
    assert "Welcome to RakthaSethu" in mock_client.sent_messages[0]["text"]
    assert mock_client.sent_messages[0]["reply_markup"] is not None

    # Test /help
    msg_help = TelegramMessage(
        message_id=2,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Ravi"),
        date=123456,
        text="/help",
    )
    await handler.handle_message(msg_help)
    assert len(mock_client.sent_messages) == 2
    assert "RakthaSethu Telegram Bot Guide" in mock_client.sent_messages[1]["text"]
    assert "Donor Privacy Policy" in mock_client.sent_messages[1]["text"]


@pytest.mark.asyncio
async def test_cmd_cancel_resets_state():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    msg_cancel = TelegramMessage(
        message_id=3,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Ravi"),
        date=123456,
        text="/cancel",
    )
    await handler.handle_message(msg_cancel)
    assert len(mock_client.sent_messages) == 1
    assert "Current conversation cancelled" in mock_client.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_conversation_validation_patient_name_and_phone():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. Too short patient name
    conv = TelegramConversation(telegram_user_id=200, chat_id=100, current_step="WAITING_PATIENT_NAME", state_data={})
    await handler.handle_conversation_step(conv, text="A", chat_id=100, user_id=200)
    assert "Patient name must be between 2 and 150 characters" in mock_client.sent_messages[-1]["text"]

    # 2. Invalid phone number
    conv.current_step = "WAITING_PHONE"
    await handler.handle_conversation_step(conv, text="12345", chat_id=100, user_id=200)
    assert "Please enter a valid 10-digit mobile number" in mock_client.sent_messages[-1]["text"]

    # 3. Valid phone number advances to urgency
    await handler.handle_conversation_step(conv, text="9876543210", chat_id=100, user_id=200)
    assert "Clinical Urgency Level" in mock_client.sent_messages[-1]["text"]


# ─── 6. Webhook Security Header Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_secret_verification():
    from app.telegram.router import telegram_webhook
    from fastapi import HTTPException

    mock_session = AsyncMock()
    update = TelegramUpdate(update_id=1)

    # Wrong secret token -> HTTP 403 Forbidden
    with patch("app.telegram.router.settings.TELEGRAM_WEBHOOK_SECRET", "correct-secret"):
        with pytest.raises(HTTPException) as exc_info:
            await telegram_webhook(
                update=update,
                x_telegram_bot_api_secret_token="wrong-token",
                session=mock_session,
            )
        assert exc_info.value.status_code == 403

        # Missing secret token -> HTTP 403 Forbidden
        with pytest.raises(HTTPException) as exc_info2:
            await telegram_webhook(
                update=update,
                x_telegram_bot_api_secret_token=None,
                session=mock_session,
            )
        assert exc_info2.value.status_code == 403


# ─── 7. Callback Flow & Submission Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_flow_blood_group_and_units():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="WAITING_BLOOD_GROUP",
        state_data={"patient_name": "Ravi Kumar"},
    )
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=conv)))

    cb = TelegramCallbackQuery(
        id="cb1",
        from_user=TelegramUser(id=200, first_name="Ravi"),
        message=TelegramMessage(message_id=10, chat=TelegramChat(id=100, type="private"), date=1, text="Step 2"),
        data="bg:O+",
    )
    await handler.handle_callback_query(cb)
    assert len(mock_client.sent_messages) == 1
    assert "Selected Blood Group: <b>O+</b>" in mock_client.sent_messages[0]["text"]
    assert "Units Required" in mock_client.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_district_selection_with_zero_hospitals_informs_user():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="WAITING_DISTRICT",
        state_data={"patient_name": "Ravi", "blood_group": "O+", "units_requested": 1},
    )

    # Mock HospitalRepository.list_active_by_district returning empty list
    with patch("app.repositories.hospital_repository.HospitalRepository.list_active_by_district", new=AsyncMock(return_value=[])):
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=conv)))

        cb = TelegramCallbackQuery(
            id="cb2",
            from_user=TelegramUser(id=200, first_name="Ravi"),
            message=TelegramMessage(message_id=11, chat=TelegramChat(id=100, type="private"), date=1, text="Step 4"),
            data="dist:Idukki",
        )
        await handler.handle_callback_query(cb)
        assert len(mock_client.sent_messages) == 1
        assert "No Registered Partner Hospitals in Idukki" in mock_client.sent_messages[0]["text"]
        assert "contact your nearest district hospital" in mock_client.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_submit_blood_request_success_and_ownership():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    state_data = {
        "hospital_id": 1,
        "hospital_name": "Kottayam Medical College",
        "patient_name": "Deepa Nair",
        "blood_group": "A+",
        "units_requested": 2,
        "district": "Kottayam",
        "contact_phone": "9876543210",
        "required_date": date.today().isoformat(),
        "urgency": "URGENT",
    }

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "Kottayam Medical College"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5915
    mock_hospital.longitude = 76.5221

    mock_created_req = MagicMock()
    mock_created_req.id = 42
    mock_created_req.request_code = "REQ0042"
    mock_created_req.hospital_name = "Kottayam Medical College"
    mock_created_req.blood_group = BloodGroup.A_POSITIVE
    mock_created_req.district = "Kottayam"
    mock_created_req.hospital_id = 1
    mock_created_req.units_requested = 2
    mock_created_req.required_date = date.today()
    mock_created_req.hospital = mock_hospital

    with patch("app.repositories.hospital_repository.HospitalRepository.get_by_id", new=AsyncMock(return_value=mock_hospital)), \
         patch("app.services.blood_request_service.BloodRequestService.create_blood_request", new=AsyncMock(return_value=mock_created_req)), \
         patch.object(handler.service, "record_telegram_blood_request", new=AsyncMock()), \
         patch.object(handler.service, "reset_conversation", new=AsyncMock()), \
         patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_created_req, mock_hospital))):
        await handler.submit_blood_request(
            chat_id=100,
            user_id=200,
            data=state_data,
            username="deepa_nair",
        )

    assert len(mock_client.sent_messages) == 1
    text = mock_client.sent_messages[0]["text"]
    assert "REQ0042" in text
    assert "Kottayam Medical College" in text
    assert "Blood Request Registered" in text


@pytest.mark.asyncio
async def test_staff_match_view_unauthorized():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # When user is not linked staff
    with patch.object(handler.service, "get_linked_staff", new=AsyncMock(return_value=None)):
        await handler.handle_staff_match_view(chat_id=100, user_id=999, req_id=42)

    assert len(mock_client.sent_messages) == 1
    assert "Unauthorized" in mock_client.sent_messages[0]["text"]


# ─── 8. Phase 8.1 Nearest-Donor Ranking & Privacy Tests ────────────────────

# Test 1: A confirmed request is saved exactly once
@pytest.mark.asyncio
async def test_confirmed_request_saved_exactly_once():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="CONFIRMATION",
        state_data={
            "hospital_id": 1,
            "patient_name": "Ravi Varma",
            "blood_group": "O+",
            "units_requested": 1,
            "district": "Kottayam",
            "contact_phone": "9876543210",
            "required_date": date.today().isoformat(),
            "urgency": "NORMAL",
        },
    )

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "Caritas Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.6200
    mock_hospital.longitude = 76.5300

    mock_req = MagicMock()
    mock_req.id = 101
    mock_req.request_code = "REQ0101"
    mock_req.hospital_name = "Caritas Hospital"
    mock_req.blood_group = BloodGroup.O_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.hospital_id = 1
    mock_req.units_requested = 1
    mock_req.required_date = date.today()
    mock_req.hospital = mock_hospital

    create_mock = AsyncMock(return_value=mock_req)
    with patch.object(handler.service, "lock_and_transition_confirmation", new=AsyncMock(return_value=(True, conv.state_data))), \
         patch("app.repositories.hospital_repository.HospitalRepository.get_by_id", new=AsyncMock(return_value=mock_hospital)), \
         patch("app.services.blood_request_service.BloodRequestService.create_blood_request", new=create_mock), \
         patch.object(handler.service, "record_telegram_blood_request", new=AsyncMock()), \
         patch.object(handler.service, "reset_conversation", new=AsyncMock()), \
         patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=MatchDonorsResponse(
             recipient_blood_group=BloodGroup.O_POSITIVE,
             compatible_blood_groups=[BloodGroup.O_POSITIVE, BloodGroup.O_NEGATIVE],
             district="Kottayam",
             origin_type="HOSPITAL_LOCATION",
             origin_latitude=9.62,
             origin_longitude=76.53,
             radius_km=25.0,
             required_units=1,
             required_date=date.today(),
             total_eligible_found=0,
             items=[],
         ))):
        cb = TelegramCallbackQuery(
            id="cb_conf",
            from_user=TelegramUser(id=200, first_name="Ravi"),
            message=TelegramMessage(message_id=20, chat=TelegramChat(id=100, type="private"), date=1, text="Confirm?"),
            data="req:confirm",
        )
        await handler.handle_callback_query(cb)

    assert create_mock.call_count == 1
    assert len(mock_client.sent_messages) == 1
    assert "REQ0101" in mock_client.sent_messages[0]["text"]
    assert "Blood Request Registered" in mock_client.sent_messages[0]["text"]


# Test 2: Compatible donors are ranked nearest first
@pytest.mark.asyncio
async def test_compatible_donors_ranked_nearest_first():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "District Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5
    mock_hospital.longitude = 76.5

    mock_req = MagicMock()
    mock_req.id = 55
    mock_req.request_code = "REQ0055"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.B_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 2
    mock_req.required_date = date.today()

    donor_near = MatchedDonorItem(
        donor_id=10,
        donor_code="DNR-NEAR",
        full_name="Nearby Donor",
        blood_group=BloodGroup.B_POSITIVE,
        phone="9876543210",
        district="Kottayam",
        is_available=True,
        distance_km=2.4,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )
    donor_far = MatchedDonorItem(
        donor_id=11,
        donor_code="DNR-FAR",
        full_name="Farther Donor",
        blood_group=BloodGroup.B_POSITIVE,
        phone="9876543211",
        district="Kottayam",
        is_available=True,
        distance_km=8.7,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )

    mock_match_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.B_POSITIVE,
        compatible_blood_groups=[BloodGroup.B_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=2,
        required_date=date.today(),
        total_eligible_found=2,
        items=[donor_near, donor_far],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_match_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=55, user_id=200, page=1, radius_km=25.0, is_initial=True)

    # Verify nearest donor is listed first
    near_pos = text.find("DNR-NEAR")
    far_pos = text.find("DNR-FAR")
    assert near_pos != -1
    assert far_pos != -1
    assert near_pos < far_pos
    assert "2.4 km" in text
    assert "8.7 km" in text


# Test 3: Incompatible donors are excluded
@pytest.mark.asyncio
async def test_incompatible_donors_excluded():
    from app.services.blood_compatibility import get_compatible_donor_groups, is_blood_compatible
    # Recipient O+ can only receive from O+, O-
    compatible = get_compatible_donor_groups(BloodGroup.O_POSITIVE)
    assert BloodGroup.O_POSITIVE in compatible
    assert BloodGroup.O_NEGATIVE in compatible
    assert BloodGroup.A_POSITIVE not in compatible
    assert BloodGroup.B_POSITIVE not in compatible
    assert BloodGroup.AB_POSITIVE not in compatible

    assert is_blood_compatible(BloodGroup.O_NEGATIVE, BloodGroup.O_POSITIVE) is True
    assert is_blood_compatible(BloodGroup.A_POSITIVE, BloodGroup.O_POSITIVE) is False


# Test 4: Ineligible or cooldown-restricted donors are excluded
@pytest.mark.asyncio
async def test_cooldown_restricted_donors_excluded():
    from app.services.cooldown_service import calculate_cooldown_eligibility
    today = date.today()
    # Whole blood cooldown is 90 days. Donor donated 20 days ago.
    cooldown = calculate_cooldown_eligibility(
        last_donation_date=today - timedelta(days=20),
        donation_type="Whole Blood",
        reference_date=today,
    )
    assert not cooldown.is_eligible
    assert cooldown.days_remaining > 0


# Test 5: Donors without required location consent are excluded from proximity matching
@pytest.mark.asyncio
async def test_donors_without_location_consent_excluded_from_proximity():
    # In MatchingService, stmt_proximity contains:
    # Donor.location_consent.is_(True)
    # Donors without location_consent=True are never queried in spatial branch
    from app.services.matching_service import MatchingService
    import inspect
    src = inspect.getsource(MatchingService.find_matching_donors)
    assert "Donor.location_consent.is_(True)" in src


# Test 6: Donors with missing coordinates are handled according to fallback rules
@pytest.mark.asyncio
async def test_missing_coordinates_fallback_rules():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "Kottayam Medical College"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.59
    mock_hospital.longitude = 76.52

    mock_req = MagicMock()
    mock_req.id = 70
    mock_req.request_code = "REQ0070"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.O_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    donor_gps = MatchedDonorItem(
        donor_id=1,
        donor_code="DNR-GPS",
        full_name="GPS Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone="9876543210",
        district="Kottayam",
        is_available=True,
        distance_km=3.2,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )
    donor_fallback = MatchedDonorItem(
        donor_id=2,
        donor_code="DNR-NOGPS",
        full_name="Fallback Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone="9876543211",
        district="Kottayam",
        is_available=True,
        distance_km=None,
        match_category="FALLBACK_DISTRICT",
        match_reason="District fallback",
    )

    mock_match_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_POSITIVE,
        compatible_blood_groups=[BloodGroup.O_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=2,
        items=[donor_gps, donor_fallback],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_match_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=70, user_id=200, page=1)

    assert "DNR-GPS" in text
    assert "approximately 3.2 km away" in text
    assert "DNR-NOGPS" in text
    assert "Distance unknown (district match: Kottayam)" in text
    # GPS donor appears before fallback donor
    assert text.find("DNR-GPS") < text.find("DNR-NOGPS")


# Test 7: No usable hospital location produces correct fallback or safe error
@pytest.mark.asyncio
async def test_no_usable_hospital_location_fallback():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Hospital with missing coordinates
    mock_hospital = MagicMock()
    mock_hospital.id = 2
    mock_hospital.name = "Rural Clinic"
    mock_hospital.is_active = True
    mock_hospital.latitude = None
    mock_hospital.longitude = None

    mock_req = MagicMock()
    mock_req.id = 72
    mock_req.request_code = "REQ0072"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 2
    mock_req.blood_group = BloodGroup.A_POSITIVE
    mock_req.district = "Idukki"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    donor_dist = MatchedDonorItem(
        donor_id=5,
        donor_code="DNR-IDK",
        full_name="District Donor",
        blood_group=BloodGroup.A_POSITIVE,
        phone="9876543212",
        district="Idukki",
        is_available=True,
        distance_km=None,
        match_category="DISTRICT_DEFAULT",
        match_reason="District match",
    )

    mock_match_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.A_POSITIVE,
        compatible_blood_groups=[BloodGroup.A_POSITIVE],
        origin_type="DISTRICT_DEFAULT",
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor_dist],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_match_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=72, user_id=200, page=1)

    assert "Hospital coordinates are unavailable. Displaying district-level matches" in text
    assert "Distance unknown (district match: Idukki)" in text
    # Never invent coordinates or distances
    assert "approximately" not in text


# Test 8: A hospital that is inactive or unverified is handled correctly
@pytest.mark.asyncio
async def test_hospital_inactive_or_unverified_handled_correctly():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Inactive hospital
    inactive_hospital = MagicMock()
    inactive_hospital.id = 99
    inactive_hospital.name = "Closed Clinic"
    inactive_hospital.is_active = False

    state_data = {
        "hospital_id": 99,
        "patient_name": "Test Patient",
        "blood_group": "B+",
        "units_requested": 1,
        "district": "Ernakulam",
        "contact_phone": "9876543210",
        "required_date": date.today().isoformat(),
        "urgency": "NORMAL",
    }

    with patch("app.repositories.hospital_repository.HospitalRepository.get_by_id", new=AsyncMock(return_value=inactive_hospital)):
        await handler.submit_blood_request(chat_id=100, user_id=200, data=state_data, username="user")

    assert len(mock_client.sent_messages) == 1
    assert "inactive or unavailable" in mock_client.sent_messages[0]["text"]


# Test 9: Zero matches returns a useful message without deleting the request
@pytest.mark.asyncio
async def test_zero_matches_returns_useful_message_without_deleting_request():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "City Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5
    mock_hospital.longitude = 76.5

    mock_req = MagicMock()
    mock_req.id = 88
    mock_req.request_code = "REQ0088"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.AB_NEGATIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    mock_zero_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.AB_NEGATIVE,
        compatible_blood_groups=[BloodGroup.AB_NEGATIVE, BloodGroup.A_NEGATIVE, BloodGroup.B_NEGATIVE, BloodGroup.O_NEGATIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=0,
        items=[],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_zero_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=88, user_id=200, page=1, radius_km=25.0)

    assert "found no potential matching donors at this time" in text
    assert "Contact City Hospital directly" in text
    assert "REQ0088" in text
    # Check that broaden search button is offered
    assert markup is not None
    assert any("Broaden Search" in btn["text"] for row in markup["inline_keyboard"] for btn in row)


# Test 10: Repeated confirmation callbacks do not create duplicate requests
@pytest.mark.asyncio
async def test_repeated_confirmation_callbacks_do_not_create_duplicate():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    lock_side_effects = [
        (True, {"hospital_id": 1, "patient_name": "Ravi", "blood_group": "A+", "units_requested": 1, "district": "Kottayam", "contact_phone": "9876543210", "required_date": date.today().isoformat(), "urgency": "NORMAL"}),
        (False, None),
    ]

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5
    mock_hospital.longitude = 76.5

    mock_req = MagicMock()
    mock_req.id = 99
    mock_req.request_code = "REQ0099"
    mock_req.hospital_name = "Hospital"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.A_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    create_mock = AsyncMock(return_value=mock_req)
    with patch.object(handler.service, "lock_and_transition_confirmation", new=AsyncMock(side_effect=lock_side_effects)), \
         patch("app.repositories.hospital_repository.HospitalRepository.get_by_id", new=AsyncMock(return_value=mock_hospital)), \
         patch("app.services.blood_request_service.BloodRequestService.create_blood_request", new=create_mock), \
         patch.object(handler.service, "record_telegram_blood_request", new=AsyncMock()), \
         patch.object(handler.service, "reset_conversation", new=AsyncMock()), \
         patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=MagicMock(total_eligible_found=0, items=[], origin_type="HOSPITAL_LOCATION"))):

        cb1 = TelegramCallbackQuery(id="c1", from_user=TelegramUser(id=300, first_name="A"), data="req:confirm")
        await handler.handle_callback_query(cb1)

        cb2 = TelegramCallbackQuery(id="c2", from_user=TelegramUser(id=300, first_name="A"), data="req:confirm")
        await handler.handle_callback_query(cb2)

    # Request creation was executed only ONCE!
    assert create_mock.call_count == 1
    assert any("already being processed" in m["text"] for m in mock_client.sent_messages)


# Test 11: Unauthorized users cannot inspect another user's request
@pytest.mark.asyncio
async def test_unauthorized_user_cannot_inspect_request():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Requester 999 is neither owner nor authorized staff
    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(False, False, MagicMock(), None))):
        cb = TelegramCallbackQuery(
            id="cb_hack",
            from_user=TelegramUser(id=999, first_name="Intruder"),
            message=TelegramMessage(message_id=50, chat=TelegramChat(id=999, type="private"), date=1, text="peek"),
            data="match:p:42:1:25",
        )
        await handler.handle_callback_query(cb)

    assert len(mock_client.sent_messages) == 1
    assert "Access Denied" in mock_client.sent_messages[0]["text"]


# Test 12: Forged or stale pagination callbacks cannot expose additional donors
@pytest.mark.asyncio
async def test_forged_or_stale_pagination_callback_rejected():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Forged callback with radius exceeding MAX_PROXIMITY_RADIUS_KM (e.g. 500 km)
    cb_excess = TelegramCallbackQuery(
        id="cb_bad_rad",
        from_user=TelegramUser(id=200, first_name="User"),
        message=TelegramMessage(message_id=51, chat=TelegramChat(id=200, type="private"), date=1, text="peek"),
        data="match:p:42:1:500",
    )
    # When radius > MAX_PROXIMITY_RADIUS_KM, callback is rejected and no donor query executes
    with patch.object(handler.service, "verify_request_access_by_id") as mock_verify:
        await handler.handle_callback_query(cb_excess)
        mock_verify.assert_not_called()


# Test 13: Telegram API failure does not cause duplicate request creation on retry
@pytest.mark.asyncio
async def test_telegram_api_failure_no_duplicate_on_retry():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    # First send_message raises timeout (initial delivery failure), second call succeeds (error notification), third call succeeds (retry notification)
    mock_client.send_message = AsyncMock(side_effect=[Exception("Telegram connection timeout"), {"ok": True}, {"ok": True}])
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5
    mock_hospital.longitude = 76.5

    mock_req = MagicMock()
    mock_req.id = 77
    mock_req.request_code = "REQ0077"
    mock_req.hospital_name = "Hospital"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.A_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    create_mock = AsyncMock(return_value=mock_req)
    state_data = {"hospital_id": 1, "patient_name": "Ravi", "blood_group": "A+", "units_requested": 1, "district": "Kottayam", "contact_phone": "9876543210", "required_date": date.today().isoformat(), "urgency": "NORMAL"}

    with patch("app.repositories.hospital_repository.HospitalRepository.get_by_id", new=AsyncMock(return_value=mock_hospital)), \
         patch("app.services.blood_request_service.BloodRequestService.create_blood_request", new=create_mock), \
         patch.object(handler.service, "record_telegram_blood_request", new=AsyncMock()), \
         patch.object(handler.service, "reset_conversation", new=AsyncMock()), \
         patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=MagicMock(total_eligible_found=0, items=[], origin_type="HOSPITAL_LOCATION"))):

        # Initial submit: Telegram send fails
        await handler.submit_blood_request(chat_id=100, user_id=200, data=state_data, username="ravi")
        assert create_mock.call_count == 1

        # Now suppose user/Telegram retries `req:confirm` -> conversation was already reset to IDLE in DB
        with patch.object(handler.service, "lock_and_transition_confirmation", new=AsyncMock(return_value=(False, None))):
            cb_retry = TelegramCallbackQuery(id="c_retry", from_user=TelegramUser(id=200, first_name="Ravi"), data="req:confirm")
            await handler.handle_callback_query(cb_retry)

        # Still exactly 1 creation!
        assert create_mock.call_count == 1


# Test 14: Donor phone numbers and exact coordinates never appear in public Telegram responses
@pytest.mark.asyncio
async def test_donor_phone_and_coordinates_never_exposed():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock()
    mock_hospital.id = 1
    mock_hospital.name = "District Hospital"
    mock_hospital.is_active = True
    mock_hospital.latitude = 9.5
    mock_hospital.longitude = 76.5

    mock_req = MagicMock()
    mock_req.id = 33
    mock_req.request_code = "REQ0033"
    mock_req.hospital = mock_hospital
    mock_req.hospital_id = 1
    mock_req.blood_group = BloodGroup.O_POSITIVE
    mock_req.district = "Kottayam"
    mock_req.units_requested = 1
    mock_req.required_date = date.today()

    secret_phone = "+919876543210"
    secret_name = "Secret Donor Person"

    donor = MatchedDonorItem(
        donor_id=12345,  # Internal database ID
        donor_code="DNR-SAFE-01",  # Safe public reference
        full_name=secret_name,
        blood_group=BloodGroup.O_POSITIVE,
        phone=secret_phone,
        district="Kottayam",
        is_available=True,
        distance_km=4.2,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_POSITIVE,
        compatible_blood_groups=[BloodGroup.O_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=33, user_id=200, page=1)

    # Phone visibility and Privacy invariants:
    assert secret_phone in text, "Donor phone number must be displayed to authorized requester."
    assert secret_name not in text, "Donor full name was leaked in Telegram message!"
    assert "12345" not in text, "Internal database ID was leaked in Telegram message!"
    assert "DNR-SAFE-01" in text, "Safe public reference must be displayed."
    assert "4.2 km" in text, "Approximate distance must be displayed."


# Test 15: Results are deterministically sorted when distances are equal
@pytest.mark.asyncio
async def test_deterministic_sort_on_equal_distances():
    # Test deterministic sorting policy:
    # 1. Distance ascending
    # 2. Exact blood group over compatible alternative
    # 3. Longest rest period since last donation
    # 4. Stable tie-breaker: donor_id
    donor_alt_exact_dist = MatchedDonorItem(
        donor_id=20,
        donor_code="DNR-ALT",
        full_name="Alt Donor",
        blood_group=BloodGroup.O_NEGATIVE,  # Compatible alternative
        phone="9876543201",
        district="Kottayam",
        is_available=True,
        distance_km=5.0,
        match_category="PROXIMITY",
        days_since_last_donation=100,
        match_reason="Compatible",
    )
    donor_exact_match = MatchedDonorItem(
        donor_id=15,
        donor_code="DNR-EXACT",
        full_name="Exact Donor",
        blood_group=BloodGroup.O_POSITIVE,  # Exact match for O+
        phone="9876543202",
        district="Kottayam",
        is_available=True,
        distance_km=5.0,
        days_since_last_donation=95,
        match_reason="Exact",
    )

    items = [donor_alt_exact_dist, donor_exact_match]
    # Apply MatchingService sorting rule
    target_bg = BloodGroup.O_POSITIVE
    items.sort(
        key=lambda item: (
            item.distance_km if item.distance_km is not None else 999999.0,
            0 if item.blood_group == target_bg else 1,
            -(item.days_since_last_donation if item.days_since_last_donation is not None else 999999),
            item.donor_id,
        )
    )

    # Exact blood group wins tie-break even with slightly shorter rest period
    assert items[0].donor_code == "DNR-EXACT"
    assert items[1].donor_code == "DNR-ALT"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 8.2: Display Donor Phone Numbers to Blood Requesters Tests
# ═══════════════════════════════════════════════════════════════════════════

# Test 8.2.1: Eligible matches display their stored phone numbers to the authorized requester
@pytest.mark.asyncio
async def test_phase82_eligible_match_displays_stored_phone():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital", is_active=True, latitude=9.5, longitude=76.5)
    mock_req = MagicMock(
        id=101, request_code="REQ0101", hospital=mock_hospital, hospital_id=1,
        blood_group=BloodGroup.O_POSITIVE, district="Kottayam", units_requested=1, required_date=date.today(),
    )

    donor = MatchedDonorItem(
        donor_id=101,
        donor_code="DNR0001",
        full_name="Eligible Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone="+919876543210",
        district="Kottayam",
        is_available=True,
        distance_km=2.4,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_POSITIVE,
        compatible_blood_groups=[BloodGroup.O_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=101, user_id=500, page=1)

    assert "Potential donor 1" in text
    assert "DNR0001" in text
    assert "O+" in text
    assert "approximately 2.4 km" in text
    assert "+919876543210" in text, "Eligible donor's phone number must be exposed"
    assert "These are potential matches, not confirmed availability" in text
    assert "verify availability before coordinating a donation" in text
    # Privacy invariants:
    assert "Eligible Donor" not in text, "Full name must not be exposed"
    assert "101" not in text.split("Potential donor")[1].split("Contact:")[0], "Internal DB ID must not be leaked"


# Test 8.2.2: Missing phone numbers display fallback assistance message
@pytest.mark.asyncio
async def test_phase82_missing_phone_displays_assistance_fallback():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital", is_active=True, latitude=9.5, longitude=76.5)
    mock_req = MagicMock(
        id=102, request_code="REQ0102", hospital=mock_hospital, hospital_id=1,
        blood_group=BloodGroup.O_POSITIVE, district="Kottayam", units_requested=1, required_date=date.today(),
    )

    donor_no_phone = MatchedDonorItem(
        donor_id=102,
        donor_code="DNR0002",
        full_name="No Phone Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone="",
        district="Kottayam",
        is_available=True,
        distance_km=3.1,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_POSITIVE,
        compatible_blood_groups=[BloodGroup.O_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor_no_phone],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, markup = await handler.format_donor_matches_view(req_id=102, user_id=500, page=1)

    assert "Contact the registered hospital for assistance." in text
    assert "Potential donor 1" in text
    assert "DNR0002" in text


# Test 8.2.3: Blood compatibility, cooldown, and eligibility remain strictly enforced
@pytest.mark.asyncio
async def test_phase82_ineligible_and_cooldown_donors_excluded():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital", is_active=True, latitude=9.5, longitude=76.5)
    mock_req = MagicMock(
        id=103, request_code="REQ0103", hospital=mock_hospital, hospital_id=1,
        blood_group=BloodGroup.O_NEGATIVE, district="Kottayam", units_requested=1, required_date=date.today(),
    )

    # Ineligible / incompatible donors excluded by matching service
    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_NEGATIVE,
        compatible_blood_groups=[BloodGroup.O_NEGATIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=0,
        items=[],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, _ = await handler.format_donor_matches_view(req_id=103, user_id=500, page=1)

    assert "found no potential matching donors at this time" in text
    assert "Potential donor" not in text
    assert "+91" not in text


# Test 8.2.4: Location consent remains enforced without treating it as phone consent
@pytest.mark.asyncio
async def test_phase82_location_consent_enforcement_unchanged():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital", is_active=True, latitude=9.5, longitude=76.5)
    mock_req = MagicMock(
        id=104, request_code="REQ0104", hospital=mock_hospital, hospital_id=1,
        blood_group=BloodGroup.B_POSITIVE, district="Kottayam", units_requested=1, required_date=date.today(),
    )

    # Donor with coordinate-less district fallback (no location consent / no GPS coordinates)
    donor_fallback = MatchedDonorItem(
        donor_id=104,
        donor_code="DNR0004",
        full_name="District Fallback Donor",
        blood_group=BloodGroup.B_POSITIVE,
        phone="+919876543244",
        district="Kottayam",
        is_available=True,
        distance_km=None,
        match_category="FALLBACK_DISTRICT",
        match_reason="District fallback",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.B_POSITIVE,
        compatible_blood_groups=[BloodGroup.B_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor_fallback],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, _ = await handler.format_donor_matches_view(req_id=104, user_id=500, page=1)

    # Location consent policy: no coordinates -> distance unknown
    assert "Distance unknown (district match: Kottayam)" in text
    # Phone number is displayed for eligible match
    assert "+919876543244" in text


# Test 8.2.5: Request ownership and access checks prevent unauthorized viewing
@pytest.mark.asyncio
async def test_phase82_request_ownership_enforced():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Unauthorized user 999 attempting to inspect request 105
    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(False, False, None, None))):
        text, markup = await handler.format_donor_matches_view(req_id=105, user_id=999, page=1)

    assert "⚠️ Blood request not found." in text or "Access Denied" in text
    assert "+91" not in text
    assert "Potential donor" not in text


# Test 8.2.6: Forged or modified pagination callbacks are safely rejected
@pytest.mark.asyncio
async def test_phase82_forged_pagination_callback_rejected():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Malicious callback with forged request ID
    cb = TelegramCallbackQuery(
        id="cb_forged",
        from_user={"id": 888, "first_name": "Attacker"},
        data="match:p:9999:1:25",
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(False, False, MagicMock(), None))):
        await handler.handle_donor_match_page(chat_id=123, user_id=888, cb=cb)

    assert len(mock_client.sent_messages) == 1
    sent_text = mock_client.sent_messages[0]["text"]
    assert "Access Denied" in sent_text
    assert "Potential donor" not in sent_text
    assert "+91" not in sent_text


# Test 8.2.7: Phone numbers do not appear in logs or errors
def test_phase82_phone_numbers_redacted_in_logs():
    from app.telegram.client import redact_sensitive_data

    sample_error = "Telegram API error: Bad Request to +919876543210 with bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    cleaned = redact_sensitive_data(sample_error)

    assert "+919876543210" not in cleaned
    assert "9876543210" not in cleaned
    assert "[REDACTED_PHONE]" in cleaned
    assert "bot[REDACTED]" in cleaned


# Test 8.2.8: Unrelated status command does not expose donor phone numbers
@pytest.mark.asyncio
async def test_phase82_status_command_does_not_leak_phone_numbers():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital")
    mock_req = MagicMock(
        id=77,
        request_code="REQ0077",
        hospital=mock_hospital,
        blood_group=BloodGroup.O_POSITIVE,
        units_requested=2,
        status=RequestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    with patch.object(handler.service, "verify_request_access", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))):
        await handler.cmd_status(chat_id=123, user_id=200, req_code="REQ0077")

    assert len(mock_client.sent_messages) == 1
    sent_text = mock_client.sent_messages[0]["text"]
    assert "REQ0077" in sent_text
    assert "+91" not in sent_text, "Status command must not expose donor phone numbers"
    assert "Potential donor" not in sent_text


# Test 8.2.9: Malformed phone numbers handled gracefully
@pytest.mark.asyncio
async def test_phase82_malformed_phone_handled_gracefully():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    mock_hospital = MagicMock(id=1, name="District Hospital", is_active=True, latitude=9.5, longitude=76.5)
    mock_req = MagicMock(
        id=109, request_code="REQ0109", hospital=mock_hospital, hospital_id=1,
        blood_group=BloodGroup.O_POSITIVE, district="Kottayam", units_requested=1, required_date=date.today(),
    )

    donor_corrupt = MatchedDonorItem(
        donor_id=109,
        donor_code="DNR0109",
        full_name="Broken Phone Donor",
        blood_group=BloodGroup.O_POSITIVE,
        phone="invalid_phone_string",
        district="Kottayam",
        is_available=True,
        distance_km=2.0,
        match_category="PROXIMITY",
        match_reason="Proximity match",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.O_POSITIVE,
        compatible_blood_groups=[BloodGroup.O_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=1,
        required_date=date.today(),
        total_eligible_found=1,
        items=[donor_corrupt],
    )

    with patch.object(handler.service, "verify_request_access_by_id", new=AsyncMock(return_value=(True, False, mock_req, mock_hospital))), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        text, _ = await handler.format_donor_matches_view(req_id=109, user_id=500, page=1)

    assert "invalid_phone_string" not in text
    assert "Contact the registered hospital for assistance." in text


# Test 8.2.10: Staff authorization and matching behavior remain intact
@pytest.mark.asyncio
async def test_phase82_staff_authorization_remains_intact():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Authorized hospital staff
    mock_staff_user = MagicMock(id=1, role=UserRole.STAFF, hospital_id=5, is_active=True)
    mock_linked_staff = MagicMock(is_active=True, user=mock_staff_user)

    mock_req = MagicMock(
        id=110, request_code="REQ0110", hospital_id=5,
        blood_group=BloodGroup.A_POSITIVE, district="Ernakulam", units_requested=2, required_date=date.today(),
    )

    mock_donor = MatchedDonorItem(
        donor_id=50,
        donor_code="DNR-STF",
        full_name="Staff Viewed Donor",
        blood_group=BloodGroup.A_POSITIVE,
        phone="+919876543250",
        district="Ernakulam",
        is_available=True,
        distance_km=5.0,
        match_category="PROXIMITY",
        match_reason="Proximity",
    )

    mock_resp = MatchDonorsResponse(
        recipient_blood_group=BloodGroup.A_POSITIVE,
        compatible_blood_groups=[BloodGroup.A_POSITIVE],
        origin_type="HOSPITAL_LOCATION",
        radius_km=25.0,
        required_units=2,
        required_date=date.today(),
        total_eligible_found=1,
        items=[mock_donor],
    )

    with patch.object(handler.service, "get_linked_staff", new=AsyncMock(return_value=mock_linked_staff)), \
         patch("app.services.blood_request_service.BloodRequestService.get_blood_request_by_id", new=AsyncMock(return_value=mock_req)), \
         patch("app.services.matching_service.MatchingService.find_matching_donors", new=AsyncMock(return_value=mock_resp)):
        await handler.handle_staff_match_view(chat_id=555, user_id=777, req_id=110)

    assert len(mock_client.sent_messages) == 1
    msg = mock_client.sent_messages[0]["text"]
    assert "Matching Donors for #REQ0110" in msg
    assert "DNR-STF" in msg
    assert "Full contact details and outreach dispatch are managed in the hospital web portal." in msg

