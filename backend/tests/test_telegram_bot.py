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

    mock_created_req = MagicMock()
    mock_created_req.id = 42
    mock_created_req.request_code = "REQ0042"
    mock_created_req.hospital_name = "Kottayam Medical College"

    with patch("app.services.blood_request_service.BloodRequestService.create_blood_request", new=AsyncMock(return_value=mock_created_req)):
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
    assert "Blood Request Submitted Successfully" in text


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
