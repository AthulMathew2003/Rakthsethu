import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.enums import BloodGroup
from app.models.donor import Donor
from app.models.telegram import (
    TelegramConversation,
    TelegramDonor,
    TelegramDonorReviewCase,
)
from app.telegram.handlers import TelegramHandler, normalize_phone_number
from app.telegram.schemas import (
    TelegramCallbackQuery,
    TelegramChat,
    TelegramContact,
    TelegramLocation,
    TelegramMessage,
    TelegramUser,
)
from app.telegram.service import TelegramService
from tests.test_telegram_bot import MockTelegramClient, create_mock_session


# ─── 1. Main Menu Preservation Tests ────────────────────────────────────────

def test_main_menu_preserves_all_options():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    kb = handler.build_main_menu_keyboard()
    rows = kb["inline_keyboard"]
    all_buttons = [btn for row in rows for btn in row]
    callbacks = [btn["callback_data"] for btn in all_buttons]
    texts = [btn["text"] for btn in all_buttons]

    # Must preserve existing options
    assert "menu:requestblood" in callbacks
    assert "menu:register_donor" in callbacks
    assert "menu:status" in callbacks
    assert "menu:link" in callbacks
    assert "menu:help" in callbacks

    assert any("Request Blood" in t for t in texts)
    assert any("Register as Donor" in t for t in texts)
    assert any("Check Request Status" in t for t in texts)
    assert any("Staff Link" in t for t in texts)
    assert any("Help" in t for t in texts)


@pytest.mark.asyncio
async def test_start_without_active_registration():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    msg = TelegramMessage(
        message_id=1,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="/start",
    )
    await handler.handle_message(msg)

    assert len(mock_client.sent_messages) == 1
    assert "Welcome to RakthaSethu" in mock_client.sent_messages[0]["text"]
    assert mock_client.sent_messages[0]["reply_markup"] == handler.build_main_menu_keyboard()


@pytest.mark.asyncio
async def test_start_with_active_registration_shows_continue_and_cancel():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_NAME",
        state_data={"full_name": "Athul Mathew"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    msg = TelegramMessage(
        message_id=2,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="/start",
    )
    await handler.handle_message(msg)

    assert len(mock_client.sent_messages) == 1
    text = mock_client.sent_messages[0]["text"]
    assert "Incomplete Donor Registration in Progress" in text
    kb = mock_client.sent_messages[0]["reply_markup"]["inline_keyboard"]
    callbacks = [btn["callback_data"] for row in kb for btn in row]
    assert "reg:resume" in callbacks
    assert "reg:cancel" in callbacks


@pytest.mark.asyncio
async def test_resume_and_cancel_callbacks():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_NAME",
        state_data={},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Test Resume
    cb_resume = TelegramCallbackQuery(
        id="cb1",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=10,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:resume",
    )
    await handler.handle_callback_query(cb_resume)
    assert any("Please enter your <b>Full Name</b>" in m["text"] for m in mock_client.sent_messages)

    # Test Cancel
    cb_cancel = TelegramCallbackQuery(
        id="cb2",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=11,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:cancel",
    )
    await handler.handle_callback_query(cb_cancel)
    assert any("Current conversation cancelled" in m["text"] for m in mock_client.sent_messages)


# ─── 2. Step 1: Consent Workflow Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_step1_consent_flow():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Start via menu callback
    cb_start = TelegramCallbackQuery(
        id="cb_start",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=1,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="menu:register_donor",
    )
    await handler.handle_callback_query(cb_start)
    assert any("Voluntary Donor Registration" in m["text"] for m in mock_client.sent_messages)
    assert any("Information Collected & Purpose" in m["text"] for m in mock_client.sent_messages)

    # Decline consent
    cb_no = TelegramCallbackQuery(
        id="cb_no",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=2,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:consent_no",
    )
    await handler.handle_callback_query(cb_no)
    assert any("Registration cancelled. Details are only collected with your explicit consent" in m["text"] for m in mock_client.sent_messages)

    # Accept consent
    cb_yes = TelegramCallbackQuery(
        id="cb_yes",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=3,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:consent_yes",
    )
    await handler.handle_callback_query(cb_yes)
    assert any("Please enter your <b>Full Name</b>" in m["text"] for m in mock_client.sent_messages)


# ─── 3. Step 2: Personal Details Collection Tests ───────────────────────────

@pytest.mark.asyncio
async def test_step2_full_name_validation():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_NAME",
        state_data={"consent_given": True},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Invalid short name
    msg_short = TelegramMessage(
        message_id=4,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="A",
    )
    await handler.handle_message(msg_short)
    assert "Please enter a valid name" in mock_client.sent_messages[-1]["text"]

    # Invalid symbols
    msg_sym = TelegramMessage(
        message_id=5,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="Athul<script>",
    )
    await handler.handle_message(msg_sym)
    assert "Please enter a valid name" in mock_client.sent_messages[-1]["text"]

    # Valid name
    msg_valid = TelegramMessage(
        message_id=6,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="Athul Mathew",
    )
    await handler.handle_message(msg_valid)
    assert "Select your <b>Blood Group</b>" in mock_client.sent_messages[-1]["text"]


@pytest.mark.asyncio
async def test_step2_blood_group_selection():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_BG",
        state_data={"full_name": "Athul Mathew"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    cb_bg = TelegramCallbackQuery(
        id="cb_bg",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=7,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg_bg:O+",
    )
    await handler.handle_callback_query(cb_bg)
    assert any("Selected Blood Group" in m["text"] for m in mock_client.sent_messages)
    assert any("Please enter your <b>Age</b>" in m["text"] for m in mock_client.sent_messages)


@pytest.mark.asyncio
async def test_step2_age_and_dob_validation():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_AGE",
        state_data={"full_name": "Athul Mathew", "blood_group": "O+"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Underage
    msg_under = TelegramMessage(
        message_id=8,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="16",
    )
    await handler.handle_message(msg_under)
    assert "at least 18 years old" in mock_client.sent_messages[-1]["text"]

    # Overage
    msg_over = TelegramMessage(
        message_id=9,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="72",
    )
    await handler.handle_message(msg_over)
    assert "up to 65 years of age" in mock_client.sent_messages[-1]["text"]

    # Invalid text
    msg_invalid = TelegramMessage(
        message_id=10,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="notanage",
    )
    await handler.handle_message(msg_invalid)
    assert "Please enter your age" in mock_client.sent_messages[-1]["text"]

    # Valid DOB YYYY-MM-DD
    msg_dob = TelegramMessage(
        message_id=11,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="2000-01-15",
    )
    await handler.handle_message(msg_dob)
    assert "Select your <b>Home District</b>" in mock_client.sent_messages[-1]["text"]


@pytest.mark.asyncio
async def test_step2_district_selection():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_DISTRICT",
        state_data={"full_name": "Athul Mathew", "blood_group": "O+", "age": 24},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    cb_dist = TelegramCallbackQuery(
        id="cb_dist",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=12,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg_dist:Ernakulam",
    )
    await handler.handle_callback_query(cb_dist)
    assert any("District: <b>Ernakulam</b>" in m["text"] for m in mock_client.sent_messages)
    assert any("Step 4 of 5: Mobile Phone Verification" in m["text"] for m in mock_client.sent_messages)
    # Check that native Share Contact button was provided
    share_contact_msg = [m for m in mock_client.sent_messages if "Share Phone Number" in str(m.get("reply_markup"))]
    assert len(share_contact_msg) > 0


# ─── 4. Step 3: Phone Number Verification Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_step3_phone_verification_rejects_typed_number_and_foreign_contact():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_PHONE_SHARE",
        state_data={"full_name": "Athul Mathew", "blood_group": "O+", "district": "Ernakulam"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. Typed phone number rejection
    msg_typed = TelegramMessage(
        message_id=13,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="9876543210",
    )
    await handler.handle_message(msg_typed)
    assert "Typed phone numbers cannot be verified" in mock_client.sent_messages[-1]["text"]

    # 2. Foreign contact rejection (user_id mismatch)
    msg_foreign = TelegramMessage(
        message_id=14,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        contact=TelegramContact(
            phone_number="+919876543210",
            first_name="Other",
            user_id=999,  # Mismatched ID!
        ),
    )
    await handler.handle_message(msg_foreign)
    assert "The shared contact does not match this Telegram account" in mock_client.sent_messages[-1]["text"]

    # 3. Valid native contact sharing
    msg_valid_contact = TelegramMessage(
        message_id=15,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        contact=TelegramContact(
            phone_number="+919876543210",
            first_name="Athul",
            user_id=200,  # Matches sender ID!
        ),
    )
    await handler.handle_message(msg_valid_contact)
    assert "Telegram Verification Code" in mock_client.sent_messages[-1]["text"]
    assert "it is not independent proof of mobile-network ownership" in mock_client.sent_messages[-1]["text"]


@pytest.mark.asyncio
async def test_step3_otp_verification_flow_and_limits():
    valid_otp = "481920"
    otp_hash = hashlib.sha256(valid_otp.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_OTP",
        state_data={
            "phone": "+919876543210",
            "otp_hash": otp_hash,
            "otp_sent_at": (now - timedelta(seconds=65)).isoformat(),
            "otp_expires_at": (now + timedelta(minutes=10)).isoformat(),
            "otp_attempts": 0,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. Incorrect OTP
    msg_wrong = TelegramMessage(
        message_id=16,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="000000",
    )
    await handler.handle_message(msg_wrong)
    assert "Incorrect verification code" in mock_client.sent_messages[-1]["text"]

    # 2. Resend code issues a fresh OTP and resets attempts
    msg_resend = TelegramMessage(
        message_id=17,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="/resend",
    )
    await handler.handle_message(msg_resend)
    resend_msg = mock_client.sent_messages[-1]["text"]
    assert "New Telegram Verification Code" in resend_msg

    # Extract newly issued OTP from message (between <code> and </code>)
    new_otp = resend_msg.split("<code>")[1].split("</code>")[0]

    # 3. Entering the newly issued OTP advances to Location Consent
    msg_correct = TelegramMessage(
        message_id=18,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text=new_otp,
    )
    await handler.handle_message(msg_correct)
    assert "Proximity Matching & Location Consent" in mock_client.sent_messages[-1]["text"]


# ─── 5. Step 4: Location Consent & Coordinates Validation ───────────────────

@pytest.mark.asyncio
async def test_step4_location_consent_and_validation():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_LOC_CONSENT",
        state_data={
            "full_name": "Athul Mathew",
            "blood_group": "O+",
            "district": "Ernakulam",
            "phone": "+919876543210",
            "phone_verified": True,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # Accept location consent -> requests native location
    cb_loc_yes = TelegramCallbackQuery(
        id="cb_loc_yes",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=19,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg_loc:consent_yes",
    )
    await handler.handle_callback_query(cb_loc_yes)
    assert any("Share Current Location" in str(m.get("reply_markup")) for m in mock_client.sent_messages)

    # Reject typed place names
    conv.current_step = "REG_LOCATION"
    msg_typed_place = TelegramMessage(
        message_id=20,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="Kaloor, Kochi",
    )
    await handler.handle_message(msg_typed_place)
    assert "Typed place names or addresses cannot be used" in mock_client.sent_messages[-1]["text"]

    # Valid native location shared
    msg_loc = TelegramMessage(
        message_id=21,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        location=TelegramLocation(latitude=9.9816, longitude=76.2999),
    )
    await handler.handle_message(msg_loc)
    assert any("GPS coordinates received securely" in m["text"] for m in mock_client.sent_messages)
    assert any("Donor Registration Summary" in m["text"] for m in mock_client.sent_messages)


@pytest.mark.asyncio
async def test_step4_mandatory_location_rejects_skip_and_declining_consent():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_LOCATION",
        state_data={
            "full_name": "Athul Mathew",
            "blood_group": "O+",
            "district": "Ernakulam",
            "phone": "+919876543210",
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. Attempting to skip location is rejected
    msg_skip = TelegramMessage(
        message_id=22,
        chat=TelegramChat(id=100, type="private"),
        from_user=TelegramUser(id=200, first_name="Athul"),
        date=123456,
        text="Skip Location",
    )
    await handler.handle_message(msg_skip)
    assert any("GPS Location Mandatory" in m["text"] for m in mock_client.sent_messages)

    # 2. Declining location consent cancels registration
    cb_loc_no = TelegramCallbackQuery(
        id="cb_loc_no",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=23,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg_loc:consent_no",
    )
    await handler.handle_callback_query(cb_loc_no)
    assert any("Registration Cancelled" in m["text"] for m in mock_client.sent_messages)
    assert any("District-only fallback registration is not permitted" in m["text"] for m in mock_client.sent_messages)


@pytest.mark.asyncio
async def test_step4_mandatory_location_prevents_submission_without_gps():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_CONFIRM",
        state_data={
            "full_name": "Athul Mathew",
            "blood_group": "O+",
            "district": "Ernakulam",
            "phone": "+919876543210",
            "location_consent": False,
            "latitude": None,
            "longitude": None,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    cb_confirm = TelegramCallbackQuery(
        id="cb_conf",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=24,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:confirm",
    )
    await handler.handle_callback_query(cb_confirm)
    assert any("GPS Location Mandatory" in m["text"] for m in mock_client.sent_messages)
    assert any("Registration cannot be submitted without valid GPS coordinates" in m["text"] for m in mock_client.sent_messages)


@pytest.mark.asyncio
async def test_existing_donor_linking_preserves_availability():
    mock_session = create_mock_session(None)
    service = TelegramService(mock_session)

    existing_donor = MagicMock(
        id=99,
        donor_code="DNR-EXIST",
        full_name="Athul Mathew",
        blood_group=BloodGroup.O_POSITIVE,
        phone="+919876543210",
        district="Kottayam",
        is_active=True,
        is_available=False,  # Currently unavailable (e.g. cooldown)
    )

    with patch("app.repositories.donor_repository.DonorRepository.get_by_phone", new=AsyncMock(return_value=existing_donor)), \
         patch.object(service, "record_telegram_donor", new=AsyncMock()):
        status, updated_donor = await service.save_registered_donor(
            telegram_user_id=200,
            chat_id=100,
            username="athul_m",
            data={
                "full_name": "Athul Mathew",
                "blood_group": "O+",
                "district": "Ernakulam",
                "phone": "+919876543210",
                "location_consent": True,
                "latitude": 9.9816,
                "longitude": 76.2999,
            },
        )

    assert status == "UPDATED"
    # Crucial requirement: existing availability is NOT overwritten
    assert updated_donor.is_available is False
    assert updated_donor.district == "Ernakulam"
    assert updated_donor.location_consent is True


# ─── 6. Step 5: Summary Formatting, Masking, and Editing ────────────────────

@pytest.mark.asyncio
async def test_step5_summary_masking_and_editing():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_CONFIRM",
        state_data={
            "full_name": "Athul Mathew",
            "blood_group": "O+",
            "age": 24,
            "district": "Ernakulam",
            "phone": "+919876543210",
            "location_consent": True,
            "latitude": 9.9816,
            "longitude": 76.2999,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    await handler.send_registration_summary(chat_id=100, user_id=200, conv=conv)
    summary_msg = mock_client.sent_messages[-1]["text"]
    assert "Athul Mathew" in summary_msg
    assert "O+" in summary_msg
    assert "Ernakulam" in summary_msg
    # Phone must be masked!
    assert "+9198****3210" in summary_msg
    assert "+919876543210" not in summary_msg
    assert "GPS Proximity Enabled" in summary_msg

    # Test editing options
    cb_edit = TelegramCallbackQuery(
        id="cb_edit",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=23,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:edit",
    )
    await handler.handle_callback_query(cb_edit)
    assert any("Which detail would you like to update?" in m["text"] for m in mock_client.sent_messages)


# ─── 7. Step 6: Save Donor Record & Conflict Handling ───────────────────────

@pytest.mark.asyncio
async def test_step6_submission_new_donor():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_CONFIRM",
        state_data={
            "full_name": "Athul Mathew",
            "blood_group": "O+",
            "district": "Ernakulam",
            "phone": "+919876543210",
            "location_consent": True,
            "latitude": 9.9816,
            "longitude": 76.2999,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    cb_confirm = TelegramCallbackQuery(
        id="cb_conf",
        from_user=TelegramUser(id=200, first_name="Athul", username="athul_m"),
        message=TelegramMessage(
            message_id=24,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:confirm",
    )

    # Mock save_registered_donor returning new donor
    mock_donor = MagicMock(
        id=42,
        donor_code="DNR-TEST01",
        full_name="Athul Mathew",
        blood_group=BloodGroup.O_POSITIVE,
        phone="+919876543210",
        district="Ernakulam",
        is_available=True,
    )
    with patch.object(handler.service, "save_registered_donor", new=AsyncMock(return_value=("CREATED", mock_donor))):
        await handler.handle_callback_query(cb_confirm)

    assert any("Registration Successful" in m["text"] for m in mock_client.sent_messages)
    assert any("DNR-TEST01" in m["text"] for m in mock_client.sent_messages)
    assert any("Welcome to the RakthaSethu network" in m["text"] for m in mock_client.sent_messages)


@pytest.mark.asyncio
async def test_step6_conflict_creates_admin_review_case():
    conv = TelegramConversation(
        telegram_user_id=200,
        chat_id=100,
        current_step="REG_CONFIRM",
        state_data={
            "full_name": "New Person",
            "blood_group": "B+",
            "district": "Thrissur",
            "phone": "+919876543210",
            "location_consent": True,
            "latitude": 10.5276,
            "longitude": 76.2144,
        },
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    cb_confirm = TelegramCallbackQuery(
        id="cb_conf",
        from_user=TelegramUser(id=200, first_name="Athul"),
        message=TelegramMessage(
            message_id=25,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
        ),
        data="reg:confirm",
    )

    # Mock save_registered_donor returning REVIEW_CASE
    mock_case = MagicMock(id=1, status="PENDING")
    with patch.object(handler.service, "save_registered_donor", new=AsyncMock(return_value=("REVIEW_CASE", mock_case))):
        await handler.handle_callback_query(cb_confirm)

    assert any("Administrative Review" in m["text"] for m in mock_client.sent_messages)
    assert any("A donor profile with this phone number is already registered under differing details" in m["text"] for m in mock_client.sent_messages)


# ─── 8. Revoke Location Consent Command Test ────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_revokelocation():
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. No linked donor record
    with patch.object(handler.service, "revoke_donor_location", new=AsyncMock(return_value=(False, "No active voluntary donor registration was found for this Telegram account.", None))):
        msg = TelegramMessage(
            message_id=26,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
            text="/revokelocation",
        )
        await handler.handle_message(msg)
        assert "No active voluntary donor registration was found" in mock_client.sent_messages[-1]["text"]

    # 2. Successfully revoked
    with patch.object(handler.service, "revoke_donor_location", new=AsyncMock(return_value=(True, "Your GPS location consent has been successfully revoked. You will now be matched based on your district only.", "DNR001"))):
        msg = TelegramMessage(
            message_id=27,
            chat=TelegramChat(id=100, type="private"),
            from_user=TelegramUser(id=200, first_name="Athul"),
            date=123456,
            text="/revokelocation",
        )
        await handler.handle_message(msg)
        assert "GPS location consent has been successfully revoked" in mock_client.sent_messages[-1]["text"]
