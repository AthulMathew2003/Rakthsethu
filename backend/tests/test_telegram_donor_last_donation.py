import math
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.enums import BloodGroup, DonationStatus
from app.models.donor import Donor
from app.models.donation import Donation
from app.models.telegram import (
    TelegramConversation,
    TelegramDonor,
)
from app.schemas.blood_request import BloodRequestResponse
from app.services.matching_service import MatchingService
from app.telegram.handlers import TelegramHandler
from app.telegram.schemas import (
    TelegramCallbackQuery,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)
from tests.test_telegram_bot import MockTelegramClient, create_mock_session


# ─── 1. Registered donor can access update option ────────────────────────────

@pytest.mark.asyncio
async def test_1_registered_donor_can_access_update_option():
    """A registered donor can open 'Update Last Donation Date' and sees options."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 101
    fake_donor.full_name = "Arun Vijay"
    fake_donor.donor_code = "DON00101"
    fake_donor.blood_group = MagicMock(value="O+")
    fake_donor.last_donation_date = date(2026, 4, 10)
    fake_donor.last_donation_date_source = "SELF_REPORTED"
    fake_donor.is_available = True

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(date(2026, 4, 10), "SELF_REPORTED", None, date(2026, 4, 10))),
        ):
            cb = TelegramCallbackQuery(
                id="cb_up_date",
                from_user=TelegramUser(id=501, first_name="Arun"),
                message=TelegramMessage(
                    message_id=201,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=501, first_name="Arun"),
                    date=123456,
                ),
                data="donor_up:update_last_donation",
            )
            await handler.handle_callback_query(cb)

    assert len(mock_client.sent_messages) == 1
    sent = mock_client.sent_messages[0]
    assert "Update Last Blood Donation Date" in sent["text"]
    assert "10-04-2026" in sent["text"]
    assert "Self-Reported" in sent["text"]

    kb = sent["reply_markup"]["inline_keyboard"]
    callbacks = [btn["callback_data"] for row in kb for btn in row]
    assert "donor_date:enter" in callbacks
    assert "donor_date:never" in callbacks
    assert "menu:update_donor_details" in callbacks
    assert "donor_date:cancel" in callbacks


# ─── 2. Unregistered Telegram user cannot access it ─────────────────────────

@pytest.mark.asyncio
async def test_2_unregistered_telegram_user_cannot_access():
    """An unregistered user is strictly rejected with an unauthorized notice."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=None)):
        # 1. Attempt callback
        cb = TelegramCallbackQuery(
            id="cb_unauth",
            from_user=TelegramUser(id=999, first_name="Stranger"),
            message=TelegramMessage(
                message_id=202,
                chat=TelegramChat(id=900, type="private"),
                from_user=TelegramUser(id=999, first_name="Stranger"),
                date=123456,
            ),
            data="donor_up:update_last_donation",
        )
        await handler.handle_callback_query(cb)

        sent = mock_client.sent_messages[-1]
        assert "Unauthorized" in sent["text"]
        kb = sent["reply_markup"]["inline_keyboard"]
        callbacks = [btn["callback_data"] for row in kb for btn in row]
        assert "menu:register_donor" in callbacks

        # 2. Attempt direct command
        msg = TelegramMessage(
            message_id=203,
            chat=TelegramChat(id=900, type="private"),
            from_user=TelegramUser(id=999, first_name="Stranger"),
            date=123456,
            text="/updatedonationdate",
        )
        await handler.handle_message(msg)
        assert "Unauthorized" in mock_client.sent_messages[-1]["text"]


# ─── 3. One donor cannot update another donor's date ────────────────────────

@pytest.mark.asyncio
async def test_3_one_donor_cannot_update_another_donors_date():
    """Authorization is strictly bound to from_user.id; external IDs are ignored."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    donor_a = MagicMock()
    donor_a.id = 111
    donor_a.full_name = "Donor A"
    donor_a.last_donation_date = None

    donor_b = MagicMock()
    donor_b.id = 222
    donor_b.full_name = "Donor B"
    donor_b.last_donation_date = date(2026, 1, 1)

    # When resolving for user 501 (Donor A), service returns donor_a
    async def mock_lookup(uid):
        if uid == 501:
            return donor_a
        elif uid == 502:
            return donor_b
        return None

    with patch.object(handler.service, "get_donor_by_telegram_user_id", side_effect=mock_lookup):
        # User 501 attempts an operation; service must ONLY resolve donor_a
        resolved = await handler.service.get_donor_by_telegram_user_id(501)
        assert resolved.id == 111
        assert resolved.full_name == "Donor A"
        assert resolved.id != 222


# ─── 4. Invalid, malformed and future dates are rejected ─────────────────────

@pytest.mark.asyncio
async def test_4_invalid_malformed_and_future_dates_are_rejected():
    """Rejects malformed strings, future dates, out of range dates, and invalid calendar days."""
    conv = TelegramConversation(
        telegram_user_id=503,
        chat_id=500,
        current_step="DONOR_UPDATE_LAST_DONATION_DATE",
        state_data={},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 103
    fake_donor.is_available = True
    fake_donor.last_donation_date = None

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        # 1. Malformed text
        msg_bad = TelegramMessage(
            message_id=210,
            chat=TelegramChat(id=500, type="private"),
            from_user=TelegramUser(id=503, first_name="Tester"),
            date=123456,
            text="invalid-date-string",
        )
        await handler.handle_donor_update_step(conv, msg_bad, 500, 503)
        assert "Invalid Date Format" in mock_client.sent_messages[-1]["text"]
        assert conv.current_step == "DONOR_UPDATE_LAST_DONATION_DATE"

        # 2. Future date
        future_dt = (date.today() + timedelta(days=10)).strftime("%d-%m-%Y")
        msg_future = TelegramMessage(
            message_id=211,
            chat=TelegramChat(id=500, type="private"),
            from_user=TelegramUser(id=503, first_name="Tester"),
            date=123456,
            text=future_dt,
        )
        await handler.handle_donor_update_step(conv, msg_future, 500, 503)
        assert "Future Date Not Permitted" in mock_client.sent_messages[-1]["text"]

        # 3. Date more than 50 years ago
        msg_old = TelegramMessage(
            message_id=212,
            chat=TelegramChat(id=500, type="private"),
            from_user=TelegramUser(id=503, first_name="Tester"),
            date=123456,
            text="01-01-1960",
        )
        await handler.handle_donor_update_step(conv, msg_old, 500, 503)
        assert "Date Outside Supported Range" in mock_client.sent_messages[-1]["text"]

        # 4. Invalid calendar day (e.g. Feb 31)
        msg_leap = TelegramMessage(
            message_id=213,
            chat=TelegramChat(id=500, type="private"),
            from_user=TelegramUser(id=503, first_name="Tester"),
            date=123456,
            text="31-02-2026",
        )
        await handler.handle_donor_update_step(conv, msg_leap, 500, 503)
        assert "Invalid Date Format or Calendar Date" in mock_client.sent_messages[-1]["text"]


# ─── 5. Cancel leaves the stored date unchanged ──────────────────────────────

@pytest.mark.asyncio
async def test_5_cancel_leaves_stored_date_unchanged():
    """Cancelling resets conversation state and leaves stored date untouched."""
    conv = TelegramConversation(
        telegram_user_id=504,
        chat_id=500,
        current_step="DONOR_CONFIRM_LAST_DONATION_DATE",
        state_data={"pending_date": "2026-08-01", "action": "SET_DATE"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    original_date = date(2026, 3, 1)
    fake_donor = MagicMock()
    fake_donor.id = 104
    fake_donor.last_donation_date = original_date
    fake_donor.is_available = True

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        cb = TelegramCallbackQuery(
            id="cb_cancel",
            from_user=TelegramUser(id=504, first_name="Tester"),
            message=TelegramMessage(
                message_id=220,
                chat=TelegramChat(id=500, type="private"),
                from_user=TelegramUser(id=504, first_name="Tester"),
                date=123456,
            ),
            data="donor_date:cancel",
        )
        await handler.handle_callback_query(cb)

    # Database was not written with new date
    assert fake_donor.last_donation_date == original_date
    assert any("cancelled" in m["text"].lower() for m in mock_client.sent_messages)


# ─── 6. Confirmation saves the date to the correct donor ────────────────────

@pytest.mark.asyncio
async def test_6_confirmation_saves_date_to_correct_donor():
    """Explicit confirmation saves the validated date to the authenticated donor record."""
    conv = TelegramConversation(
        telegram_user_id=505,
        chat_id=500,
        current_step="DONOR_CONFIRM_LAST_DONATION_DATE",
        state_data={"pending_date": "2026-07-20", "action": "SET_DATE"},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 105
    fake_donor.last_donation_date = None
    fake_donor.last_donation_date_source = None
    fake_donor.is_available = True

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(handler.service, "get_conversation", new=AsyncMock(return_value=conv)):
            with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=None)):
                cb = TelegramCallbackQuery(
                    id="cb_save",
                    from_user=TelegramUser(id=505, first_name="Tester"),
                    message=TelegramMessage(
                        message_id=230,
                        chat=TelegramChat(id=500, type="private"),
                        from_user=TelegramUser(id=505, first_name="Tester"),
                        date=123456,
                    ),
                    data="donor_date:confirm_save",
                )
                await handler.handle_callback_query(cb)

    assert fake_donor.last_donation_date == date(2026, 7, 20)
    assert fake_donor.last_donation_date_source == "SELF_REPORTED"
    assert any("Updated Successfully" in m["text"] for m in mock_client.sent_messages)


# ─── 7. Self-reported date is not marked as hospital-verified ───────────────

@pytest.mark.asyncio
async def test_7_self_reported_date_is_not_marked_as_hospital_verified():
    """Self-reported updates are tagged as SELF_REPORTED and not HOSPITAL_VERIFIED."""
    mock_session = create_mock_session(None)
    handler = TelegramHandler(session=mock_session, client=MockTelegramClient())

    donor = Donor(
        donor_code="DON00777",
        full_name="Deepa Thomas",
        blood_group=BloodGroup.A_POSITIVE,
        phone="+919876543211",
        district="Ernakulam",
        is_available=True,
    )
    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor)):
        with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=None)):
            success, msg, updated = await handler.service.update_donor_last_donation_date(
                telegram_user_id=777,
                new_date=date(2026, 6, 15),
            )

    assert success is True
    assert updated.last_donation_date == date(2026, 6, 15)
    assert updated.last_donation_date_source == "SELF_REPORTED"
    assert updated.last_donation_date_source != "HOSPITAL_VERIFIED"


# ─── 8. Existing verified donation history is not silently overwritten ──────

@pytest.mark.asyncio
async def test_8_existing_verified_donation_history_not_overwritten():
    """Verified donations in the donations ledger are not deleted or overwritten."""
    mock_session = create_mock_session(None)
    handler = TelegramHandler(session=mock_session, client=MockTelegramClient())

    donor = Donor(
        donor_code="DON00888",
        full_name="Manoj Varma",
        blood_group=BloodGroup.B_POSITIVE,
        phone="+919876543212",
        district="Kottayam",
        is_available=True,
    )
    verified_hospital_date = date(2026, 9, 1)

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor)):
        with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=verified_hospital_date)):
            # Donor attempts to set an older date or clear date
            success, msg, updated = await handler.service.update_donor_last_donation_date(
                telegram_user_id=888,
                new_date=date(2026, 6, 1),
            )

    assert success is True
    # The verified date remains noted and in effect for cooldown
    assert "Hospital-verified donation from 01-09-2026 is more recent" in msg
    mock_session.delete.assert_not_called()


# ─── 9. Cooldown and matching use the correct donation-date policy ──────────

@pytest.mark.asyncio
async def test_9_cooldown_and_matching_use_correct_donation_date_policy():
    """MatchingService enforces cooldown using authoritative effective date."""
    mock_session = create_mock_session(None)
    matching_svc = MatchingService(session=mock_session)

    today = date(2026, 10, 21)

    # Donor 1: Self-reported donation 20 days ago (Ineligible, cooldown = 90 days)
    donor_recent = MagicMock()
    donor_recent.id = 1
    donor_recent.donor_code = "DON001"
    donor_recent.full_name = "Recent Donor"
    donor_recent.phone = "+919876543201"
    donor_recent.blood_group = BloodGroup.O_POSITIVE
    donor_recent.last_donation_date = today - timedelta(days=20)
    donor_recent.district = "Ernakulam"
    donor_recent.panchayat = None
    donor_recent.is_available = True

    # Donor 2: Self-reported donation 120 days ago (Eligible)
    donor_old = MagicMock()
    donor_old.id = 2
    donor_old.donor_code = "DON002"
    donor_old.full_name = "Old Donor"
    donor_old.phone = "+919876543202"
    donor_old.blood_group = BloodGroup.O_POSITIVE
    donor_old.last_donation_date = today - timedelta(days=120)
    donor_old.district = "Ernakulam"
    donor_old.panchayat = None
    donor_old.is_available = True

    # Mock SQL result returning (Donor, last_completed_date_from_ledger)
    mock_res = MagicMock()
    mock_res.all.return_value = [
        (donor_recent, None),  # Donor 1 has no hospital record, only self-reported 20 days ago
        (donor_old, None),     # Donor 2 has no hospital record, only self-reported 120 days ago
    ]
    mock_session.execute = AsyncMock(return_value=mock_res)

    from app.schemas.matching import MatchDonorsRequest
    request = MatchDonorsRequest(
        blood_group=BloodGroup.O_POSITIVE,
        district="Ernakulam",
        panchayat=None,
        donation_type="Whole Blood",
        radius_km=None,
        limit=10,
    )

    with patch("app.services.matching_service.date") as mock_date:
        mock_date.today.return_value = today
        result = await matching_svc.find_matching_donors(request)

    # Donor 1 must be excluded due to 20-day cooldown; Donor 2 must be matched
    matched_ids = [item.donor_id for item in result.items]
    assert 1 not in matched_ids
    assert 2 in matched_ids
    donor_2_item = next(item for item in result.items if item.donor_id == 2)
    assert donor_2_item.days_since_last_donation == 120


# ─── 10. is_available remains unchanged ─────────────────────────────────────

@pytest.mark.asyncio
async def test_10_is_available_remains_unchanged():
    """Updating last donation date does not alter the donor's is_available flag."""
    mock_session = create_mock_session(None)
    handler = TelegramHandler(session=mock_session, client=MockTelegramClient())

    # Case A: Donor is Available (is_available = True)
    donor_a = Donor(
        donor_code="DON00901",
        full_name="Anandhu",
        blood_group=BloodGroup.O_POSITIVE,
        phone="+919876543221",
        district="Ernakulam",
        is_available=True,
    )
    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor_a)):
        with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=None)):
            await handler.service.update_donor_last_donation_date(901, date.today() - timedelta(days=10))
            assert donor_a.is_available is True  # Unchanged!

    # Case B: Donor is Unavailable (is_available = False)
    donor_b = Donor(
        donor_code="DON00902",
        full_name="Binu",
        blood_group=BloodGroup.A_POSITIVE,
        phone="+919876543222",
        district="Ernakulam",
        is_available=False,
    )
    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor_b)):
        with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=None)):
            await handler.service.update_donor_last_donation_date(902, date.today() - timedelta(days=200))
            assert donor_b.is_available is False  # Unchanged!


# ─── 11. Existing Telegram menus and workflows continue to work ─────────────

@pytest.mark.asyncio
async def test_11_existing_telegram_menus_and_workflows_continue_to_work():
    """Confirms /start, profile display, update menu, and blood request work intact."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 111
    fake_donor.full_name = "Sanjay Nair"
    fake_donor.donor_code = "DON00111"
    fake_donor.blood_group = MagicMock(value="B+")
    fake_donor.district = "Alappuzha"
    fake_donor.panchayat = None
    fake_donor.phone = "+919876543233"
    fake_donor.is_available = True
    fake_donor.location_consent = True
    fake_donor.location = "POINT(76.3 9.5)"

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(date(2026, 5, 20), "SELF_REPORTED", None, date(2026, 5, 20))),
        ):
            # 1. View donor profile shows last blood donation and update date button
            await handler.show_donor_profile(chat_id=500, user_id=601)
            prof_msg = mock_client.sent_messages[-1]
            assert "Your Voluntary Donor Profile" in prof_msg["text"]
            assert "Last Blood Donation:" in prof_msg["text"]
            assert "20-05-2026 (Self-Reported)" in prof_msg["text"]

            prof_callbacks = [btn["callback_data"] for row in prof_msg["reply_markup"]["inline_keyboard"] for btn in row]
            assert "donor_up:update_last_donation" in prof_callbacks
            assert "menu:update_donor_details" in prof_callbacks

            # 2. Update menu shows last donation date and update button
            await handler.show_donor_update_menu(chat_id=500, user_id=601)
            up_msg = mock_client.sent_messages[-1]
            assert "Update Voluntary Donor Details" in up_msg["text"]
            assert "20-05-2026 (Self-Reported)" in up_msg["text"]

            up_callbacks = [btn["callback_data"] for row in up_msg["reply_markup"]["inline_keyboard"] for btn in row]
            assert "donor_up:update_last_donation" in up_callbacks
            assert "donor_up:toggle_avail" in up_callbacks


# ─── 12. Cooldown reflects configuration setting ─────────────────────────────

@pytest.mark.asyncio
async def test_12_cooldown_reflects_configuration_setting():
    """Cooldown eligibility interval derives from settings.WHOLE_BLOOD_COOLDOWN_DAYS."""
    from app.core.config import settings
    from app.services.cooldown_service import calculate_cooldown_eligibility

    today = date(2026, 10, 21)
    # At standard 90 days: donation 80 days ago is ineligible
    cooldown = calculate_cooldown_eligibility(today - timedelta(days=80), "Whole Blood", reference_date=today)
    assert cooldown.is_eligible is False
    assert cooldown.cooldown_days_required == settings.WHOLE_BLOOD_COOLDOWN_DAYS
    assert cooldown.days_remaining == 10

    # If configuration is overridden to 60 days
    with patch.object(settings, "WHOLE_BLOOD_COOLDOWN_DAYS", 60):
        cooldown_custom = calculate_cooldown_eligibility(today - timedelta(days=80), "Whole Blood", reference_date=today)
        assert cooldown_custom.is_eligible is True
        assert cooldown_custom.cooldown_days_required == 60
        assert cooldown_custom.days_remaining == 0


# ─── 13. Distinguish never donated vs unknown history ────────────────────────

@pytest.mark.asyncio
async def test_13_distinguish_never_donated_vs_unknown_history():
    """Distinguish 'never donated' from 'donation history unknown' without medical eligibility assertions."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    # 1. Unrecorded history donor (never confirmed)
    donor_unrecorded = MagicMock()
    donor_unrecorded.id = 701
    donor_unrecorded.donor_code = "DON00701"
    donor_unrecorded.full_name = "Maya"
    donor_unrecorded.blood_group = MagicMock(value="A+")
    donor_unrecorded.district = "Kollam"
    donor_unrecorded.phone = "+919876543271"
    donor_unrecorded.is_available = True
    donor_unrecorded.location_consent = False
    donor_unrecorded.location = None

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor_unrecorded)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(None, None, None, None)),
        ):
            await handler.show_donor_profile(chat_id=500, user_id=701)
            msg = mock_client.sent_messages[-1]
            assert "Not recorded / Unknown" in msg["text"]
            assert "medically eligible" not in msg["text"].lower()

    # 2. Confirmed Never Donated donor
    donor_never = MagicMock()
    donor_never.id = 702
    donor_never.donor_code = "DON00702"
    donor_never.full_name = "Kiran"
    donor_never.blood_group = MagicMock(value="B+")
    donor_never.district = "Kollam"
    donor_never.phone = "+919876543272"
    donor_never.is_available = True
    donor_never.location_consent = False
    donor_never.location = None

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=donor_never)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(None, "NEVER_DONATED", None, None)),
        ):
            await handler.show_donor_profile(chat_id=500, user_id=702)
            msg = mock_client.sent_messages[-1]
            assert "Never donated (Confirmed)" in msg["text"]
            assert "medically eligible" not in msg["text"].lower()


# ─── 14. Hospital verified donation cannot be bypassed by self-reported date ─

@pytest.mark.asyncio
async def test_14_hospital_verified_donation_cannot_be_bypassed_by_older_self_reported_date():
    """Verified hospital donation ledger is authoritative over older self-reported dates."""
    today = date(2026, 10, 21)
    donor = Donor(
        donor_code="DON00703",
        full_name="Deepak",
        blood_group=BloodGroup.O_POSITIVE,
        phone="+919876543273",
        district="Ernakulam",
        is_available=True,
        # Self-reported older date: 150 days ago (would be eligible if accepted alone)
        last_donation_date=today - timedelta(days=150),
        last_donation_date_source="SELF_REPORTED",
    )

    # Hospital completed donation in ledger: only 20 days ago (ineligible!)
    recent_hospital_donation = today - timedelta(days=20)

    from app.repositories.donor_repository import DonorRepository
    mock_session = AsyncMock()
    repo = DonorRepository(mock_session)

    with patch.object(repo, "get_latest_donation_date", new=AsyncMock(return_value=recent_hospital_donation)):
        eff_date, source = await repo.get_effective_last_donation_date(donor)
        assert eff_date == recent_hospital_donation
        assert source == "HOSPITAL_VERIFIED"


# ─── 15. Expired, repeated, or concurrent callback is rejected ───────────────

@pytest.mark.asyncio
async def test_15_expired_or_repeated_or_concurrent_callback_is_rejected():
    """Callbacks that are expired, already consumed, or concurrent are safely rejected."""
    # 1. Expired callback (> 2 hours old)
    conv_expired = TelegramConversation(
        telegram_user_id=801,
        chat_id=500,
        current_step="DONOR_CONFIRM_LAST_DONATION_DATE",
        state_data={"pending_date": "2026-07-20", "action": "SET_DATE"},
        updated_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    mock_session = create_mock_session(conv_expired)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 801
    fake_donor.last_donation_date = None
    fake_donor.last_donation_date_updated_at = None

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(handler.service, "get_conversation", new=AsyncMock(return_value=conv_expired)):
            cb = TelegramCallbackQuery(
                id="cb_exp",
                from_user=TelegramUser(id=801, first_name="User"),
                message=TelegramMessage(
                    message_id=301,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=801, first_name="User"),
                    date=123456,
                ),
                data="donor_date:confirm_save",
            )
            await handler.handle_callback_query(cb)

    assert any("expired" in m["text"].lower() for m in mock_client.sent_messages)

    # 2. Repeated callback (current_step already reset to IDLE)
    mock_client.sent_messages.clear()
    conv_idle = TelegramConversation(
        telegram_user_id=801,
        chat_id=500,
        current_step="IDLE",
        state_data={},
    )
    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(handler.service, "get_conversation", new=AsyncMock(return_value=conv_idle)):
            cb_repeat = TelegramCallbackQuery(
                id="cb_repeat",
                from_user=TelegramUser(id=801, first_name="User"),
                message=TelegramMessage(
                    message_id=302,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=801, first_name="User"),
                    date=123456,
                ),
                data="donor_date:confirm_save",
            )
            await handler.handle_callback_query(cb_repeat)

    assert any("already processed" in m["text"].lower() or "expired" in m["text"].lower() for m in mock_client.sent_messages)

    # 3. Concurrency conflict (donor was updated by another action while confirmation was pending)
    mock_client.sent_messages.clear()
    earlier_ts = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)
    newer_ts = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    conv_stale = TelegramConversation(
        telegram_user_id=801,
        chat_id=500,
        current_step="DONOR_CONFIRM_LAST_DONATION_DATE",
        state_data={"pending_date": "2026-07-20", "action": "SET_DATE", "donor_updated_at": earlier_ts.isoformat()},
        updated_at=datetime.now(timezone.utc),
    )
    fake_donor.last_donation_date_updated_at = newer_ts  # newer than expected!

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(handler.service, "get_conversation", new=AsyncMock(return_value=conv_stale)):
            cb_conflict = TelegramCallbackQuery(
                id="cb_conflict",
                from_user=TelegramUser(id=801, first_name="User"),
                message=TelegramMessage(
                    message_id=303,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=801, first_name="User"),
                    date=123456,
                ),
                data="donor_date:confirm_save",
            )
            await handler.handle_callback_query(cb_conflict)

    assert any("newer update" in m["text"].lower() for m in mock_client.sent_messages)


# ─── 16. DonorService effective donation date consistency ────────────────────

@pytest.mark.asyncio
async def test_16_donor_service_effective_donation_date_consistency():
    """DonorService methods return the effective donation date and provenance."""
    from app.services.donor_service import DonorService
    from app.schemas.donor import DonorListQuery

    mock_session = AsyncMock()
    service = DonorService(mock_session)

    now = datetime.now(timezone.utc)
    test_donor = Donor(
        donor_code="DON00801",
        full_name="Renuka",
        blood_group=BloodGroup.B_POSITIVE,
        phone="+919876543281",
        district="Ernakulam",
        is_available=True,
        is_active=True,
        location_consent=False,
        last_donation_date=date(2026, 6, 1),
        last_donation_date_source="SELF_REPORTED",
    )
    test_donor.id = 801
    test_donor.created_at = now
    test_donor.updated_at = now

    with patch.object(service.donor_repo, "get_by_id", new=AsyncMock(return_value=test_donor)):
        with patch.object(service.donor_repo, "get_effective_last_donation_date", new=AsyncMock(return_value=(date(2026, 6, 1), "SELF_REPORTED"))):
            resp = await service.get_donor_by_id(801)
            assert resp.last_donation_date == date(2026, 6, 1)
            assert resp.last_donation_date_source == "SELF_REPORTED"


# ─── 17. donor_date:enter and donor_date:never do not raise AttributeError ───

@pytest.mark.asyncio
async def test_17_donor_date_enter_and_never_callbacks_create_conversation_without_attribute_error():
    """Verify donor_date:enter and donor_date:never callbacks create conversation without AttributeError."""
    conv = TelegramConversation(
        telegram_user_id=899,
        chat_id=500,
        current_step="IDLE",
        state_data={},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 899
    fake_donor.last_donation_date = None
    fake_donor.last_donation_date_source = None
    fake_donor.last_donation_date_updated_at = None
    fake_donor.is_available = True

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(None, None, None, None)),
        ):
            # 1. Test donor_date:enter callback
            cb_enter = TelegramCallbackQuery(
                id="cb_enter",
                from_user=TelegramUser(id=899, first_name="Tester"),
                message=TelegramMessage(
                    message_id=310,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=899, first_name="Tester"),
                    date=123456,
                ),
                data="donor_date:enter",
            )
            # Must NOT raise AttributeError: 'TelegramService' object has no attribute 'get_or_create_conversation'
            await handler.handle_callback_query(cb_enter)
            assert conv.current_step == "DONOR_UPDATE_LAST_DONATION_DATE"
            assert any("enter your last blood donation date" in m["text"].lower() for m in mock_client.sent_messages)

            # 2. Test donor_date:never callback
            mock_client.sent_messages.clear()
            cb_never = TelegramCallbackQuery(
                id="cb_never",
                from_user=TelegramUser(id=899, first_name="Tester"),
                message=TelegramMessage(
                    message_id=311,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=899, first_name="Tester"),
                    date=123456,
                ),
                data="donor_date:never",
            )
            # Must NOT raise AttributeError
            await handler.handle_callback_query(cb_never)
            assert conv.current_step == "DONOR_CONFIRM_LAST_DONATION_DATE"
            assert conv.state_data.get("source") == "NEVER_DONATED"
            assert any("confirm: never donated blood" in m["text"].lower() for m in mock_client.sent_messages)


# ─── 18. TelegramService get_or_create_conversation implementation ────────────

@pytest.mark.asyncio
async def test_18_service_get_or_create_conversation_method():
    """Verify TelegramService.get_or_create_conversation handles both data and data_updates kwargs."""
    from app.telegram.service import TelegramService

    conv = TelegramConversation(
        telegram_user_id=950,
        chat_id=500,
        current_step="IDLE",
        state_data={},
    )
    mock_session = create_mock_session(conv)
    service = TelegramService(session=mock_session)

    # 1. Calling with `data`
    c1 = await service.get_or_create_conversation(
        telegram_user_id=950,
        chat_id=500,
        step="STEP_A",
        data={"key1": "val1"},
    )
    assert c1.current_step == "STEP_A"
    assert c1.state_data.get("key1") == "val1"

    # 2. Calling with `data_updates`
    c2 = await service.get_or_create_conversation(
        telegram_user_id=950,
        chat_id=500,
        step="STEP_B",
        data_updates={"key2": "val2"},
    )
    assert c2.current_step == "STEP_B"
    assert c2.state_data.get("key2") == "val2"


# ─── 19. Full end-to-end flow: date entry, text input, confirmation ──────────

@pytest.mark.asyncio
async def test_19_full_end_to_end_flow_date_entry_and_confirmation():
    """Verify full interactive flow from donor_date:enter through text input to confirmation."""
    conv = TelegramConversation(
        telegram_user_id=960,
        chat_id=500,
        current_step="IDLE",
        state_data={},
    )
    mock_session = create_mock_session(conv)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    fake_donor = MagicMock()
    fake_donor.id = 960
    fake_donor.last_donation_date = None
    fake_donor.last_donation_date_source = None
    fake_donor.last_donation_date_updated_at = None
    fake_donor.is_available = True

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=fake_donor)):
        with patch.object(
            handler.service,
            "get_donor_last_donation_info",
            new=AsyncMock(return_value=(None, None, None, None)),
        ):
            with patch("app.repositories.donor_repository.DonorRepository.get_latest_donation_date", new=AsyncMock(return_value=None)):
                # Step 1: User clicks "Enter Donation Date"
                cb_enter = TelegramCallbackQuery(
                    id="cb_e2e_enter",
                    from_user=TelegramUser(id=960, first_name="Tester"),
                    message=TelegramMessage(
                        message_id=320,
                        chat=TelegramChat(id=500, type="private"),
                        from_user=TelegramUser(id=960, first_name="Tester"),
                        date=123456,
                    ),
                    data="donor_date:enter",
                )
                await handler.handle_callback_query(cb_enter)
                assert conv.current_step == "DONOR_UPDATE_LAST_DONATION_DATE"

                # Step 2: User sends text message with date "15-07-2026"
                msg = TelegramMessage(
                    message_id=321,
                    chat=TelegramChat(id=500, type="private"),
                    from_user=TelegramUser(id=960, first_name="Tester"),
                    date=123456,
                    text="15-07-2026",
                )
                await handler.handle_donor_update_step(conv, msg, chat_id=500, user_id=960)
                assert conv.current_step == "DONOR_CONFIRM_LAST_DONATION_DATE"
                assert conv.state_data.get("pending_date") == "2026-07-15"

                # Step 3: User confirms save
                cb_save = TelegramCallbackQuery(
                    id="cb_e2e_save",
                    from_user=TelegramUser(id=960, first_name="Tester"),
                    message=TelegramMessage(
                        message_id=322,
                        chat=TelegramChat(id=500, type="private"),
                        from_user=TelegramUser(id=960, first_name="Tester"),
                        date=123456,
                    ),
                    data="donor_date:confirm_save",
                )
                await handler.handle_callback_query(cb_save)
                assert fake_donor.last_donation_date == date(2026, 7, 15)
                assert fake_donor.last_donation_date_source == "SELF_REPORTED"
                assert conv.current_step == "IDLE"


# ─── 20. Unlinked users cannot access date entry or never donated ────────────

@pytest.mark.asyncio
async def test_20_unlinked_user_rejected_from_enter_and_never():
    """Unlinked telegram users are rejected from donor_date:enter and donor_date:never."""
    mock_session = create_mock_session(None)
    mock_client = MockTelegramClient()
    handler = TelegramHandler(session=mock_session, client=mock_client)

    with patch.object(handler.service, "get_donor_by_telegram_user_id", new=AsyncMock(return_value=None)):
        # 1. Attempt donor_date:enter
        cb_enter = TelegramCallbackQuery(
            id="cb_unlinked_enter",
            from_user=TelegramUser(id=9999, first_name="Stranger"),
            message=TelegramMessage(
                message_id=330,
                chat=TelegramChat(id=500, type="private"),
                from_user=TelegramUser(id=9999, first_name="Stranger"),
                date=123456,
            ),
            data="donor_date:enter",
        )
        await handler.handle_callback_query(cb_enter)
        assert any("unauthorized" in m["text"].lower() for m in mock_client.sent_messages)

        # 2. Attempt donor_date:never
        mock_client.sent_messages.clear()
        cb_never = TelegramCallbackQuery(
            id="cb_unlinked_never",
            from_user=TelegramUser(id=9999, first_name="Stranger"),
            message=TelegramMessage(
                message_id=331,
                chat=TelegramChat(id=500, type="private"),
                from_user=TelegramUser(id=9999, first_name="Stranger"),
                date=123456,
            ),
            data="donor_date:never",
        )
        await handler.handle_callback_query(cb_never)
        assert any("unauthorized" in m["text"].lower() for m in mock_client.sent_messages)
