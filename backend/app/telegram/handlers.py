from datetime import date, datetime, timedelta, timezone
import hashlib
import logging
import math
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.phone_utils import normalize_phone_number
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency, UserRole
from app.models.telegram import TelegramConversation
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.blood_request import BloodRequestCreate
from app.services.blood_request_service import BloodRequestService
from app.services.cooldown_service import calculate_cooldown_eligibility
from app.services.matching_service import MatchingService
from app.telegram.client import TelegramClient
from app.telegram.schemas import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    TelegramCallbackQuery,
    TelegramMessage,
    TelegramUpdate,
)
from app.telegram.service import TelegramService

logger = logging.getLogger("rakthasethu.telegram.handlers")

KERALA_DISTRICTS = [
    "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha",
    "Kottayam", "Idukki", "Ernakulam", "Thrissur",
    "Palakkad", "Malappuram", "Kozhikode", "Wayanad",
    "Kannur", "Kasaragod",
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


class TelegramHandler:
    """
    Handles Telegram Bot commands, messages, and inline callback queries.
    Integrates directly with RakthaSethu business services and repositories.
    """

    def __init__(self, session: AsyncSession, client: Optional[TelegramClient] = None):
        self.session = session
        self.service = TelegramService(session)
        self.client = client or TelegramClient()

    async def process_update(self, update: TelegramUpdate) -> None:
        """Route an incoming Telegram update to the appropriate handler."""
        # 1. Deduplication and durable idempotency check
        user_id = None
        chat_id = None
        update_type = "unknown"

        if update.message:
            update_type = "message"
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id if update.message.from_user else None
        elif update.callback_query:
            update_type = "callback_query"
            user_id = update.callback_query.from_user.id
            if update.callback_query.message:
                chat_id = update.callback_query.message.chat.id

        can_proceed, status_reason = await self.service.start_update_processing(
            update_id=update.update_id,
            chat_id=chat_id,
            user_id=user_id,
            update_type=update_type,
        )

        if not can_proceed:
            logger.info("Skipping update %s (status: %s)", update.update_id, status_reason)
            return

        try:
            if update.message:
                await self.handle_message(update.message)
            elif update.callback_query:
                await self.handle_callback_query(update.callback_query)

            await self.service.mark_update_completed(update.update_id)
        except Exception as exc:
            logger.exception("Error processing Telegram update %s: %s", update.update_id, exc)
            await self.service.mark_update_failed(update.update_id, str(exc))
            if chat_id:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ An unexpected error occurred while processing your request. Please try again or type /cancel.",
                )

    # ─── Message Dispatcher ───────────────────────────────────────────────

    async def handle_message(self, message: TelegramMessage) -> None:
        text = (message.text or "").strip()
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else chat_id

        # Handle top-level slash commands
        if text.startswith("/start"):
            await self.cmd_start(chat_id, user_id)
            return
        elif text.startswith("/help") or text == "ℹ️ Help":
            await self.cmd_help(chat_id)
            return
        elif text.startswith("/cancel") or text in ("❌ Cancel", "❌ Cancel Registration"):
            await self.cmd_cancel(chat_id, user_id)
            return
        elif text.startswith("/requestblood") or text == "🩸 Request Blood":
            await self.start_request_blood(chat_id, user_id)
            return
        elif text.startswith("/registerdonor") or text.startswith("/register") or text == "📝 Register as Donor":
            await self.start_donor_registration(chat_id, user_id)
            return
        elif text.startswith("/myprofile") or text.startswith("/profile") or text == "👤 View My Donor Profile":
            await self.show_donor_profile(chat_id, user_id)
            return
        elif text.startswith("/updatedetails") or text == "✏️ Update My Details":
            await self.show_donor_update_menu(chat_id, user_id)
            return
        elif text.startswith("/updatedonationdate") or text == "🩸 Update Last Donation Date":
            await self.start_update_last_donation_flow(chat_id, user_id)
            return
        elif text.startswith("/revokelocation"):
            await self.cmd_revokelocation(chat_id, user_id)
            return
        elif text.startswith("/status") or text == "🔍 Check Request Status":
            parts = text.split()
            req_code = parts[1] if len(parts) > 1 else None
            await self.cmd_status(chat_id, user_id, req_code)
            return
        elif text.startswith("/link") or text == "🏥 Staff Link":
            parts = text.split()
            token = parts[1] if len(parts) > 1 else None
            username = message.from_user.username if message.from_user else None
            await self.cmd_link(chat_id, user_id, token, username)
            return

        # Check conversational state machine
        conv = await self.service.get_conversation(user_id)
        if conv and conv.current_step != "IDLE":
            if conv.current_step.startswith("REG_"):
                await self.handle_registration_step(conv, message, chat_id, user_id)
            elif conv.current_step.startswith("DONOR_"):
                await self.handle_donor_update_step(conv, message, chat_id, user_id)
            else:
                await self.handle_conversation_step(conv, text, chat_id, user_id)
        else:
            # Unrecognized free text message
            is_donor = bool(await self.service.get_donor_by_telegram_user_id(user_id))
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "👋 Welcome to <b>RakthaSethu</b>. Please use the menu below or type /help for available options."
                ),
                reply_markup=self.build_main_menu_keyboard(is_donor=is_donor),
            )

    # ─── Commands ─────────────────────────────────────────────────────────

    async def cmd_start(self, chat_id: int, user_id: int) -> None:
        conv = await self.service.get_conversation(user_id)
        if conv and conv.current_step.startswith("REG_") and conv.current_step not in ("IDLE", "REG_COMPLETED"):
            resume_text = (
                "🩸 <b>Welcome to RakthaSethu Blood Donation Network</b>\n\n"
                "⚠️ <b>Incomplete Donor Registration in Progress:</b>\n"
                "You have an ongoing voluntary donor registration session. "
                "Would you like to continue where you left off or cancel and start fresh?"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "▶️ Continue Registration", "callback_data": "reg:resume"}],
                    [{"text": "❌ Cancel Registration", "callback_data": "reg:cancel"}],
                    [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                    [
                        {"text": "🔍 Check Request Status", "callback_data": "menu:status"},
                        {"text": "ℹ️ Help", "callback_data": "menu:help"},
                    ],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=resume_text, reply_markup=kb)
            return

        # 1. Check if user is already a registered donor in PostgreSQL
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if donor:
            await self.service.reset_conversation(user_id)
            welcome_text = (
                f"🩸 <b>Welcome back to RakthaSethu, {donor.full_name}!</b>\n\n"
                f"Thank you for being a verified voluntary donor (<code>{donor.donor_code}</code>, {donor.blood_group.value}). "
                "Your registration is active in our network to help emergency patients in Kerala.\n\n"
                "<b>Quick Actions:</b>\n"
                "• 🩸 <b>/requestblood</b> — Submit an urgent clinical blood request\n"
                "• 👤 <b>View Profile</b> — Check your donor status and details\n"
                "• ✏️ <b>Update Details</b> — Manage availability or location consent\n"
                "• 🔍 <b>/status [CODE]</b> — Check blood request status\n"
                "• ℹ️ <b>/help</b> — Bot guide & donor privacy policies\n"
                "• 🏥 <b>/link [TOKEN]</b> — Link hospital staff account"
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return

        # 2. Check if user registration is pending administrative review
        review_case = await self.service.get_pending_donor_review_case(user_id)
        if review_case:
            await self.service.reset_conversation(user_id)
            review_text = (
                "🩸 <b>Welcome to RakthaSethu Blood Donation Network</b>\n\n"
                "ℹ️ <b>Registration Status: Pending Administrative Review</b>\n\n"
                f"Your voluntary donor registration (Case ID: <code>CASE-{review_case.id}</code>) is currently being reviewed "
                "by hospital staff due to existing record verification.\n\n"
                "• <b>Status:</b> Under Review\n"
                "• <b>Reason:</b> Conflicting donor details for this phone number.\n\n"
                "Our team will complete the verification shortly. While under review, a duplicate registration cannot be submitted.\n"
                "You can still submit clinical blood requests or check request status below:"
            )
            review_kb = {
                "inline_keyboard": [
                    [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                    [{"text": "🔍 Check Request Status", "callback_data": "menu:status"}],
                    [
                        {"text": "🏥 Staff Link", "callback_data": "menu:link"},
                        {"text": "ℹ️ Help", "callback_data": "menu:help"},
                    ],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=review_text, reply_markup=review_kb)
            return

        # 3. Standard main menu for unregistered users
        await self.service.reset_conversation(user_id)
        welcome_text = (
            "🩸 <b>Welcome to RakthaSethu Blood Donation Network</b>\n\n"
            "RakthaSethu connects patients in clinical need with verified voluntary blood donors "
            "and hospital blood banks across Kerala.\n\n"
            "<b>Quick Actions:</b>\n"
            "• 🩸 <b>/requestblood</b> — Submit an urgent clinical blood request\n"
            "• 📝 <b>/registerdonor</b> — Register as a voluntary blood donor\n"
            "• 🔍 <b>/status [CODE]</b> — Check your blood request status\n"
            "• ℹ️ <b>/help</b> — Learn how to use this service\n"
            "• 🏥 <b>/link [TOKEN]</b> — Link hospital staff account"
        )
        await self.client.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=self.build_main_menu_keyboard(is_donor=False),
        )

    async def cmd_help(self, chat_id: int) -> None:
        help_text = (
            "ℹ️ <b>RakthaSethu Telegram Bot Guide</b>\n\n"
            "<b>Public Commands:</b>\n"
            "• <code>/requestblood</code> — Guided, step-by-step submission for a clinical blood request.\n"
            "• <code>/registerdonor</code> — Register as a verified voluntary blood donor across Kerala.\n"
            "• <code>/status &lt;REQ_CODE&gt;</code> — View the progress of a request you submitted (e.g. <code>/status REQ0001</code>).\n"
            "• <code>/revokelocation</code> — Revoke GPS proximity matching consent for your donor profile at any time.\n"
            "• <code>/cancel</code> — Abort the active submission at any time.\n\n"
            "<b>Hospital Staff Commands:</b>\n"
            "• <code>/link &lt;TOKEN&gt;</code> — Link this Telegram account to your verified hospital staff portal.\n\n"
            "🔒 <b>Donor Privacy Policy:</b>\n"
            "To safeguard donor privacy, voluntary donor contact details are never exposed to arbitrary Telegram users. "
            "All donor outreach is strictly coordinated through verified hospital blood banks."
        )
        await self.client.send_message(chat_id=chat_id, text=help_text)

    async def cmd_cancel(self, chat_id: int, user_id: int) -> None:
        await self.service.reset_conversation(user_id)
        is_donor = bool(await self.service.get_donor_by_telegram_user_id(user_id))
        await self.client.send_message(
            chat_id=chat_id,
            text="❌ Current conversation cancelled. No information was submitted.\nUse the menu below whenever you wish to proceed.",
            reply_markup=self.build_main_menu_keyboard(is_donor=is_donor),
        )


    async def cmd_status(self, chat_id: int, user_id: int, req_code: Optional[str]) -> None:
        if not req_code:
            await self.client.send_message(
                chat_id=chat_id,
                text="ℹ️ Please provide your blood request code.\nExample: <code>/status REQ0001</code>",
            )
            return

        is_auth, is_staff, req, hospital = await self.service.verify_request_access(
            request_code=req_code,
            telegram_user_id=user_id,
        )

        if not req:
            await self.client.send_message(
                chat_id=chat_id,
                text=f"⚠️ No blood request found with code <code>{req_code}</code>. Please double-check your code.",
            )
            return

        if not is_auth:
            # Unauthorized access prevention
            await self.client.send_message(
                chat_id=chat_id,
                text="⛔ <b>Access Denied:</b> You are not authorized to view this blood request.\n"
                     "You can only view requests that you submitted via this Telegram account.",
            )
            return

        hosp_name = hospital.name if hospital else "Assigned Hospital"
        status_text = (
            f"🩸 <b>Blood Request Status</b>\n\n"
            f"📌 <b>Code:</b> <code>{req.request_code}</code>\n"
            f"👤 <b>Patient:</b> {req.patient_name}\n"
            f"💉 <b>Blood Group:</b> {req.blood_group.value} ({req.units_requested} Unit{'s' if req.units_requested > 1 else ''})\n"
            f"🏥 <b>Hospital:</b> {hosp_name}\n"
            f"📍 <b>District:</b> {req.district}\n"
            f"📅 <b>Target Date:</b> {req.required_date}\n"
            f"⚡ <b>Urgency:</b> {req.urgency.value}\n"
            f"📊 <b>Current Status:</b> <b>{req.status.value}</b>\n\n"
        )

        kb_rows = [
            [{"text": "📍 View Nearest Potential Donors", "callback_data": f"match:p:{req.id}:1:25"}]
        ]

        if is_staff:
            status_text += "<i>[Authorized Staff View]</i>"
            kb_rows.insert(0, [{"text": "🔍 Check Matching Donors (Staff Portal)", "callback_data": f"staff_match:{req.id}"}])
        else:
            status_text += (
                "<i>Donor outreach is actively coordinated with the hospital blood bank. "
                "Donor contact details are protected under RakthaSethu privacy rules.</i>"
            )

        await self.client.send_message(
            chat_id=chat_id,
            text=status_text,
            reply_markup={"inline_keyboard": kb_rows},
        )

    async def cmd_link(self, chat_id: int, user_id: int, token: Optional[str], username: Optional[str]) -> None:
        if not token:
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "ℹ️ <b>Hospital Staff Account Linking:</b>\n\n"
                    "1. Log in to your RakthaSethu Web Dashboard.\n"
                    "2. Navigate to your Profile/Staff settings and generate a <b>Telegram Link Token</b>.\n"
                    "3. Send <code>/link &lt;TOKEN&gt;</code> here within 10 minutes.\n\n"
                    "Example: <code>/link RST-9A2B-3C4D</code>"
                ),
            )
            return

        success, message, user = await self.service.redeem_link_token(
            plain_token=token,
            telegram_user_id=user_id,
            telegram_chat_id=chat_id,
            telegram_username=username,
        )

        if success and user:
            hosp_desc = f" at {user.hospital.name}" if user.hospital else ""
            reply = (
                f"✅ <b>Staff Account Linked Successfully!</b>\n\n"
                f"👤 <b>Name:</b> {user.full_name}\n"
                f"🛡️ <b>Role:</b> {user.role.value}\n"
                f"🏥 <b>Affiliation:</b> {hosp_desc or 'Statewide Admin'}\n\n"
                f"You now have access to staff-level request tracking and donor matching dispatch."
            )
        else:
            reply = f"❌ <b>Linking Failed:</b> {message}"

        await self.client.send_message(chat_id=chat_id, text=reply)

    # ─── Voluntary Donor Registration Flow ────────────────────────────────

    async def start_donor_registration(self, chat_id: int, user_id: int) -> None:
        """
        Initiates voluntary donor registration, with database-backed checks
        protecting against duplicate registrations.
        """
        # Guard 1: Already registered donor
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if donor:
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ <b>Already Registered as Donor:</b>\n\n"
                    f"You are already registered in the RakthaSethu network as <b>{donor.full_name}</b> "
                    f"(Donor Code: <code>{donor.donor_code}</code>, {donor.blood_group.value}).\n\n"
                    "You do not need to register again. You can view or update your details using the options below."
                ),
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return

        # Guard 2: Registration pending admin review
        review_case = await self.service.get_pending_donor_review_case(user_id)
        if review_case:
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"ℹ️ <b>Registration Under Review:</b>\n\n"
                    f"Your voluntary donor registration is currently pending administrative review (Case ID: <code>CASE-{review_case.id}</code>).\n\n"
                    "To safeguard registry accuracy, a duplicate registration cannot be created while this review is pending."
                ),
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                        [{"text": "🔍 Check Request Status", "callback_data": "menu:status"}],
                        [
                            {"text": "🏥 Staff Link", "callback_data": "menu:link"},
                            {"text": "ℹ️ Help", "callback_data": "menu:help"},
                        ],
                    ]
                },
            )
            return

        # Step 1: Consent
        await self.service.update_conversation(
            telegram_user_id=user_id,
            chat_id=chat_id,
            step="REG_CONSENT",
            data_updates={},
        )
        consent_text = (
            "📝 <b>Voluntary Donor Registration</b>\n\n"
            "Thank you for stepping forward to save lives across Kerala through the RakthaSethu network.\n\n"
            "<b>Information Collected & Purpose:</b>\n"
            "• <b>Full Name & Blood Group:</b> For clinical compatibility matching.\n"
            "• <b>Age or Date of Birth:</b> To ensure compliance with voluntary blood donation eligibility (18–65 years).\n"
            "• <b>District:</b> To match urgent requests in your home area.\n"
            "• <b>Mobile Phone Number:</b> Verified via Telegram contact sharing for urgent clinical coordination.\n"
            "• <b>GPS Location (Mandatory):</b> For proximity-based emergency matching. (Exact coordinates are never disclosed).\n\n"
            "🔒 <i>All information is protected under RakthaSethu healthcare privacy guidelines. You can cancel or revoke location consent at any time.</i>\n\n"
            "Do you consent to providing these details to join the voluntary donor registry?"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "✅ I Consent & Agree", "callback_data": "reg:consent_yes"}],
                [{"text": "❌ Decline & Cancel", "callback_data": "reg:consent_no"}],
            ]
        }
        await self.client.send_message(chat_id=chat_id, text=consent_text, reply_markup=kb)

    async def show_donor_profile(self, chat_id: int, user_id: int) -> None:
        """Displays voluntary donor profile details to the registered user."""
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if not donor:
            await self.client.send_message(
                chat_id=chat_id,
                text="ℹ️ No registered voluntary donor profile was found for this Telegram account.\nYou can register anytime from the main menu.",
                reply_markup=self.build_main_menu_keyboard(is_donor=False),
            )
            return

        eff_date, source, _, _ = await self.service.get_donor_last_donation_info(user_id)
        if eff_date:
            last_don_str = f"{eff_date.strftime('%d-%m-%Y')} ({'Hospital-Verified' if source == 'HOSPITAL_VERIFIED' else 'Self-Reported'})"
        elif source == "NEVER_DONATED":
            last_don_str = "Never donated (Confirmed)"
        else:
            last_don_str = "Not recorded / Unknown"

        avail_badge = "🟢 Available for Matching" if donor.is_available else "🟡 Temporarily Unavailable"
        loc_badge = "📍 GPS Proximity Enabled" if (donor.location_consent and donor.location is not None) else "📍 District Matching Only"
        masked_phone = self._mask_phone(donor.phone)
        panchayat_str = f"\n• <b>Panchayat / Local Body:</b> {donor.panchayat}" if getattr(donor, "panchayat", None) else ""

        profile_text = (
            "👤 <b>Your Voluntary Donor Profile</b>\n\n"
            f"• <b>Donor Code:</b> <code>{donor.donor_code}</code>\n"
            f"• <b>Full Name:</b> {donor.full_name}\n"
            f"• <b>Blood Group:</b> <b>{donor.blood_group.value}</b>\n"
            f"• <b>Home District:</b> {donor.district}{panchayat_str}\n"
            f"• <b>Last Blood Donation:</b> {last_don_str}\n"
            f"• <b>Verified Mobile:</b> <code>{masked_phone}</code>\n"
            f"• <b>Matching Status:</b> {avail_badge}\n"
            f"• <b>Location Mode:</b> {loc_badge}\n\n"
            "<i>To update your details, donation date, or location consent, choose an action below:</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🩸 Update Last Donation Date", "callback_data": "donor_up:update_last_donation"}],
                [{"text": "✏️ Update My Details", "callback_data": "menu:update_donor_details"}],
                [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                [{"text": "🏠 Main Menu", "callback_data": "menu:home"}],
            ]
        }
        await self.client.send_message(chat_id=chat_id, text=profile_text, reply_markup=kb)

    async def show_donor_update_menu(self, chat_id: int, user_id: int) -> None:
        """Shows menu allowing registered voluntary donors to safely manage settings."""
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if not donor:
            await self.client.send_message(
                chat_id=chat_id,
                text="ℹ️ No registered donor profile found to update.",
                reply_markup=self.build_main_menu_keyboard(is_donor=False),
            )
            return

        eff_date, source, _, _ = await self.service.get_donor_last_donation_info(user_id)
        if eff_date:
            last_don_str = f"{eff_date.strftime('%d-%m-%Y')} ({'Hospital-Verified' if source == 'HOSPITAL_VERIFIED' else 'Self-Reported'})"
        elif source == "NEVER_DONATED":
            last_don_str = "Never donated (Confirmed)"
        else:
            last_don_str = "Not recorded / Unknown"

        toggle_btn = "🔴 Mark as Temporarily Unavailable" if donor.is_available else "🟢 Mark as Available for Matching"
        curr_status = "Available for emergency matching" if donor.is_available else "Temporarily Unavailable"

        kb = {
            "inline_keyboard": [
                [{"text": "🩸 Update Last Donation Date", "callback_data": "donor_up:update_last_donation"}],
                [{"text": toggle_btn, "callback_data": "donor_up:toggle_avail"}],
                [{"text": "📍 Update Home District", "callback_data": "donor_up:change_district"}],
                [{"text": "🚫 Revoke GPS Location Consent", "callback_data": "donor_up:revoke_gps"}],
                [{"text": "🔙 Back to Profile", "callback_data": "menu:view_donor_profile"}],
            ]
        }
        text = (
            "✏️ <b>Update Voluntary Donor Details</b>\n\n"
            f"• <b>Current Status:</b> {curr_status}\n"
            f"• <b>Current District:</b> {donor.district}\n"
            f"• <b>Last Donation Date:</b> {last_don_str}\n\n"
            "Choose a setting to update safely:"
        )
        await self.client.send_message(chat_id=chat_id, text=text, reply_markup=kb)

    async def start_update_last_donation_flow(self, chat_id: int, user_id: int) -> None:
        """Entry point for authenticated donors to view and update their last donation date."""
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if not donor:
            await self.client.send_message(
                chat_id=chat_id,
                text="⚠️ <b>Unauthorized:</b> You must be a registered voluntary donor to update donation dates.\nPlease register from the main menu.",
                reply_markup=self.build_main_menu_keyboard(is_donor=False),
            )
            return

        eff_date, source, verified_date, self_date = await self.service.get_donor_last_donation_info(user_id)
        if eff_date:
            date_str = f"{eff_date.strftime('%d-%m-%Y')} ({'Hospital-Verified' if source == 'HOSPITAL_VERIFIED' else 'Self-Reported'})"
        elif source == "NEVER_DONATED":
            date_str = "Never donated (Confirmed)"
        else:
            date_str = "Not recorded / Unknown"

        text = (
            "🩸 <b>Update Last Blood Donation Date</b>\n\n"
            f"• <b>Currently Recorded:</b> <b>{date_str}</b>\n\n"
            "Have you donated blood recently?\n\n"
            f"• If you have donated blood, entering the date helps our emergency matching system respect your required rest period ({settings.WHOLE_BLOOD_COOLDOWN_DAYS} days for whole blood).\n"
            "• If you have never donated blood before, select <i>Never Donated</i> to record your history as a first-time donor.\n\n"
            "Please choose an option below:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "📅 Enter Donation Date", "callback_data": "donor_date:enter"}],
                [{"text": "🌱 I Have Never Donated Blood", "callback_data": "donor_date:never"}],
                [{"text": "🔙 Back to Update Menu", "callback_data": "menu:update_donor_details"}],
                [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
            ]
        }
        await self.client.send_message(chat_id=chat_id, text=text, reply_markup=kb)

    async def handle_donor_update_step(
        self,
        conv: TelegramConversation,
        message: TelegramMessage,
        chat_id: int,
        user_id: int,
    ) -> None:
        """Handles conversational text input for donor profile updates."""
        donor = await self.service.get_donor_by_telegram_user_id(user_id)
        if not donor:
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text="⚠️ <b>Unauthorized:</b> No registered donor profile was found for this Telegram account.",
                reply_markup=self.build_main_menu_keyboard(is_donor=False),
            )
            return

        text = (message.text or "").strip()

        if conv.current_step == "DONOR_UPDATE_LAST_DONATION_DATE":
            # Attempt to parse DD-MM-YYYY (or with / or .)
            parsed_date: Optional[date] = None
            clean_date_str = re.sub(r"[/.]", "-", text)
            parts = clean_date_str.split("-")
            if len(parts) == 3:
                try:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    parsed_date = date(y, m, d)
                except (ValueError, TypeError):
                    parsed_date = None

            if not parsed_date:
                err_text = (
                    "❌ <b>Invalid Date Format or Calendar Date:</b>\n\n"
                    "Please enter a valid past calendar date in the format <b>DD-MM-YYYY</b>.\n"
                    "<i>Example:</i> <code>15-08-2026</code>"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                        [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                    ]
                }
                await self.client.send_message(chat_id=chat_id, text=err_text, reply_markup=kb)
                return

            today = date.today()
            if parsed_date > today:
                err_text = (
                    "❌ <b>Future Date Not Permitted:</b>\n\n"
                    "A blood donation date cannot be in the future. Please enter a date on or before today.\n"
                    "<i>Format:</i> <b>DD-MM-YYYY</b>"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                        [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                    ]
                }
                await self.client.send_message(chat_id=chat_id, text=err_text, reply_markup=kb)
                return

            if parsed_date < today - timedelta(days=365 * 50):
                err_text = (
                    "❌ <b>Date Outside Supported Range:</b>\n\n"
                    "The donation date entered is more than 50 years in the past. Please enter a valid recent date.\n"
                    "<i>Format:</i> <b>DD-MM-YYYY</b>"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                        [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                    ]
                }
                await self.client.send_message(chat_id=chat_id, text=err_text, reply_markup=kb)
                return

            # Compute cooldown preview
            cooldown = calculate_cooldown_eligibility(parsed_date, "Whole Blood", reference_date=today)
            if cooldown.is_eligible:
                cooldown_status = f"🟢 <b>Eligible now</b> ({cooldown.days_since_last_donation} days since donation)"
            else:
                cooldown_status = f"🟡 <b>On Rest Cooldown</b> until <b>{cooldown.eligible_from.strftime('%d-%m-%Y')}</b> ({cooldown.days_remaining} days remaining)"

            # Update conversation step to confirmation
            conv.current_step = "DONOR_CONFIRM_LAST_DONATION_DATE"
            conv.state_data = {
                "pending_date": parsed_date.isoformat(),
                "action": "SET_DATE",
                "source": "SELF_REPORTED",
                "donor_updated_at": donor.last_donation_date_updated_at.isoformat() if donor.last_donation_date_updated_at else None,
            }
            await self.session.commit()

            confirm_text = (
                "📋 <b>Confirm Last Blood Donation Date</b>\n\n"
                f"• <b>Entered Date:</b> <b>{parsed_date.strftime('%d-%m-%Y')}</b>\n"
                f"• <b>Rest Period (Whole Blood):</b> {settings.WHOLE_BLOOD_COOLDOWN_DAYS} days\n"
                f"• <b>Cooldown Status:</b> {cooldown_status}\n"
                "• <b>Provenance:</b> Voluntary Donor Self-Reported\n\n"
                "<i>Note: Your emergency matching availability status (is_available) will remain unchanged.</i>\n\n"
                "Save this donation date to your profile?"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "✅ Confirm & Save", "callback_data": "donor_date:confirm_save"}],
                    [{"text": "✏️ Change Date", "callback_data": "donor_date:enter"}],
                    [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=confirm_text, reply_markup=kb)
            return

        elif conv.current_step == "DONOR_CONFIRM_LAST_DONATION_DATE":
            # If user sent text instead of tapping button, remind them
            remind_text = (
                "ℹ️ Please confirm your donation date using the buttons below, or click Change Date / Cancel:"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "✅ Confirm & Save", "callback_data": "donor_date:confirm_save"}],
                    [{"text": "✏️ Change Date", "callback_data": "donor_date:enter"}],
                    [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=remind_text, reply_markup=kb)
            return

    async def cmd_revokelocation(self, chat_id: int, user_id: int) -> None:
        """Allows voluntary donors to revoke GPS location consent at any time."""
        success, message, code = await self.service.revoke_donor_location(user_id)
        if success:
            text = (
                "📍 <b>Location Consent Revoked</b>\n\n"
                f"• <b>Donor Code:</b> <code>{code}</code>\n"
                f"• {message}\n\n"
                "You can re-enable GPS proximity matching at any time by updating your registration."
            )
        else:
            text = f"ℹ️ {message}"
        is_donor = bool(await self.service.get_donor_by_telegram_user_id(user_id))
        await self.client.send_message(chat_id=chat_id, text=text, reply_markup=self.build_main_menu_keyboard(is_donor=is_donor))

    # ─── Blood Request Guided Conversation ────────────────────────────────

    async def start_request_blood(self, chat_id: int, user_id: int) -> None:
        await self.service.update_conversation(
            telegram_user_id=user_id,
            chat_id=chat_id,
            step="WAITING_PATIENT_NAME",
            data_updates={},
        )
        await self.client.send_message(
            chat_id=chat_id,
            text=(
                "🩸 <b>New Blood Request — Step 1 of 8</b>\n\n"
                "Please enter the <b>Patient's Full Name</b> (or clinical case reference/bed number):\n\n"
                "<i>Type /cancel at any point to stop.</i>"
            ),
        )

    async def handle_conversation_step(
        self,
        conv: Any,
        text: str,
        chat_id: int,
        user_id: int,
    ) -> None:
        step = conv.current_step
        data = dict(conv.state_data or {})

        if step == "WAITING_PATIENT_NAME":
            name = text.strip()
            if len(name) < 2 or len(name) > 150:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Patient name must be between 2 and 150 characters. Please re-enter:",
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_BLOOD_GROUP",
                data_updates={"patient_name": name},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text="🩸 <b>Step 2 of 8:</b> Select the required <b>Blood Group</b>:",
                reply_markup=self.build_blood_group_keyboard(),
            )

        elif step == "WAITING_PHONE":
            # Sanitize phone
            clean_phone = re.sub(r"[^\d+]", "", text.strip())
            if len(clean_phone) < 10 or len(clean_phone) > 15:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Please enter a valid 10-digit mobile number (e.g. <code>9876543210</code>):",
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_URGENCY",
                data_updates={"contact_phone": clean_phone},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text="⚡ <b>Step 8 of 8:</b> Select the <b>Clinical Urgency Level</b>:",
                reply_markup=self.build_urgency_keyboard(),
            )

        elif step == "WAITING_DATE":
            # Date can be typed manually (YYYY-MM-DD)
            try:
                parsed_date = datetime.strptime(text.strip(), "%Y-%m-%d").date()
                if parsed_date < date.today():
                    await self.client.send_message(
                        chat_id=chat_id,
                        text="⚠️ Target date cannot be in the past. Please enter a valid date (YYYY-MM-DD):",
                    )
                    return
                await self.service.update_conversation(
                    telegram_user_id=user_id,
                    chat_id=chat_id,
                    step="WAITING_PHONE",
                    data_updates={"required_date": parsed_date.isoformat()},
                )
                await self.client.send_message(
                    chat_id=chat_id,
                    text="📞 <b>Step 7 of 8:</b> Enter the <b>Contact Phone Number</b> for coordination:",
                )
            except ValueError:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Invalid date format. Please use <code>YYYY-MM-DD</code> or choose an option above:",
                )

    # ─── Callback Queries (Inline Buttons) ────────────────────────────────

    async def handle_callback_query(self, cb: TelegramCallbackQuery) -> None:
        user_id = cb.from_user.id
        chat_id = cb.message.chat.id if cb.message else user_id
        data_str = cb.data or ""
        await self.client.answer_callback_query(cb.id)

        # 1. No-op button click (e.g. current page indicator)
        if data_str == "noop":
            return

        # 2. Donor match pagination and radius expansion dispatch
        if data_str.startswith("match:p:") or data_str.startswith("match:r:"):
            await self.handle_donor_match_page(chat_id, user_id, cb)
            return

        # 3. Staff Donor Matching Dispatch
        if data_str.startswith("staff_match:"):
            req_id_str = data_str.split(":")[1]
            try:
                req_id = int(req_id_str)
                await self.handle_staff_match_view(chat_id, user_id, req_id)
            except Exception as exc:
                logger.error("Error in staff_match: %s", exc)
            return

        # 4. Main menu navigation
        if data_str == "menu:requestblood":
            await self.start_request_blood(chat_id, user_id)
            return
        elif data_str == "menu:register_donor":
            await self.start_donor_registration(chat_id, user_id)
            return
        elif data_str == "menu:view_donor_profile":
            await self.show_donor_profile(chat_id, user_id)
            return
        elif data_str == "menu:update_donor_details":
            await self.show_donor_update_menu(chat_id, user_id)
            return
        elif data_str == "menu:home":
            await self.cmd_start(chat_id, user_id)
            return
        elif data_str == "menu:status":
            await self.client.send_message(
                chat_id=chat_id,
                text="🔍 To check a request status, send: <code>/status &lt;REQ_CODE&gt;</code>\nExample: <code>/status REQ0001</code>",
            )
            return
        elif data_str == "menu:help":
            await self.cmd_help(chat_id)
            return
        elif data_str == "menu:link":
            await self.cmd_link(chat_id, user_id, None, None)
            return

        # 4a. Registered Donor Profile Management Actions
        if data_str == "donor_up:update_last_donation":
            await self.start_update_last_donation_flow(chat_id, user_id)
            return
        elif data_str == "donor_date:enter":
            donor = await self.service.get_donor_by_telegram_user_id(user_id)
            if not donor:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ <b>Unauthorized:</b> You must be a registered voluntary donor to update your donation date.",
                    reply_markup=self.build_main_menu_keyboard(is_donor=False),
                )
                return
            await self.service.get_or_create_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="DONOR_UPDATE_LAST_DONATION_DATE",
                data={},
            )
            enter_text = (
                "📅 <b>Please enter your last blood donation date:</b>\n\n"
                "Format: <b>DD-MM-YYYY</b> (for example, <code>15-08-2026</code>)\n\n"
                "<i>Note: The date must be a past date within the last 50 years.</i>"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                    [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=enter_text, reply_markup=kb)
            return
        elif data_str == "donor_date:never":
            donor = await self.service.get_donor_by_telegram_user_id(user_id)
            if not donor:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ <b>Unauthorized:</b> You must be a registered voluntary donor.",
                    reply_markup=self.build_main_menu_keyboard(is_donor=False),
                )
                return

            _, _, verified_date, _ = await self.service.get_donor_last_donation_info(user_id)
            if verified_date:
                v_text = (
                    "ℹ️ <b>Hospital-Verified Record On File:</b>\n\n"
                    f"A hospital-verified donation from <b>{verified_date.strftime('%d-%m-%Y')}</b> is linked to your donor profile. "
                    "Clinical records cannot be cleared by self-reporting."
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                        [{"text": "🏠 Main Menu", "callback_data": "menu:home"}],
                    ]
                }
                await self.client.send_message(chat_id=chat_id, text=v_text, reply_markup=kb)
                return

            # Show confirmation for Never Donated
            await self.service.get_or_create_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="DONOR_CONFIRM_LAST_DONATION_DATE",
                data={
                    "pending_date": None,
                    "action": "CLEAR_DATE",
                    "source": "NEVER_DONATED",
                    "donor_updated_at": donor.last_donation_date_updated_at.isoformat() if donor.last_donation_date_updated_at else None,
                },
            )
            never_text = (
                "📋 <b>Confirm: Never Donated Blood</b>\n\n"
                "• <b>Status:</b> Confirmed Never Donated (First-time donor)\n"
                f"• <b>Cooldown Policy:</b> No required rest cooldown ({settings.WHOLE_BLOOD_COOLDOWN_DAYS} days whole blood cooldown does not apply).\n"
                "• <b>Clinical Note:</b> Standard health screening by medical staff is still required prior to any physical donation.\n\n"
                "Would you like to confirm that you have never donated blood?"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "✅ Confirm & Save", "callback_data": "donor_date:confirm_save"}],
                    [{"text": "🔙 Back", "callback_data": "donor_up:update_last_donation"}],
                    [{"text": "❌ Cancel", "callback_data": "donor_date:cancel"}],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=never_text, reply_markup=kb)
            return
        elif data_str == "donor_date:confirm_save":
            donor = await self.service.get_donor_by_telegram_user_id(user_id)
            if not donor:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ <b>Unauthorized:</b> You must be a registered voluntary donor.",
                    reply_markup=self.build_main_menu_keyboard(is_donor=False),
                )
                return

            conv = await self.service.get_conversation(user_id)
            if not conv or conv.current_step != "DONOR_CONFIRM_LAST_DONATION_DATE":
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ This confirmation request has expired or was already processed. Please use the menu below:",
                    reply_markup=self.build_main_menu_keyboard(is_donor=True),
                )
                return

            # Check expiration (2 hours TTL)
            if conv.updated_at:
                now_utc = datetime.now(timezone.utc)
                conv_time = conv.updated_at if conv.updated_at.tzinfo else conv.updated_at.replace(tzinfo=timezone.utc)
                if (now_utc - conv_time).total_seconds() > 7200:
                    await self.service.reset_conversation(user_id)
                    await self.client.send_message(
                        chat_id=chat_id,
                        text="⚠️ This confirmation session has expired. Please start again from the menu below:",
                        reply_markup=self.build_main_menu_keyboard(is_donor=True),
                    )
                    return

            # Prevent stale callbacks from overwriting newer updates
            expected_updated_at = conv.state_data.get("donor_updated_at")
            donor_updated_dt = getattr(donor, "last_donation_date_updated_at", None)
            current_updated_at = donor_updated_dt.isoformat() if isinstance(donor_updated_dt, datetime) else None
            if expected_updated_at and current_updated_at and expected_updated_at != current_updated_at:
                await self.service.reset_conversation(user_id)
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ A newer update to your donation record was made while this confirmation was pending. This older request has been discarded.",
                    reply_markup=self.build_main_menu_keyboard(is_donor=True),
                )
                return

            pending_date_str = conv.state_data.get("pending_date")
            target_date: Optional[date] = None
            if pending_date_str:
                try:
                    target_date = date.fromisoformat(pending_date_str)
                except (ValueError, TypeError):
                    target_date = None

            save_source = conv.state_data.get("source", "SELF_REPORTED") if target_date is None else "SELF_REPORTED"

            # Reset conversation immediately to prevent repeated/concurrent execution
            await self.service.reset_conversation(user_id)

            success, msg, updated_donor = await self.service.update_donor_last_donation_date(
                telegram_user_id=user_id,
                new_date=target_date,
                source=save_source,
            )

            if success and updated_donor:
                if target_date:
                    date_display = target_date.strftime("%d-%m-%Y")
                    rec_type = "Voluntary Donor Self-Reported"
                elif save_source == "NEVER_DONATED":
                    date_display = "Never Donated (Confirmed)"
                    rec_type = "Voluntary Donor Self-Reported (First-time donor)"
                else:
                    date_display = "Donation history unknown / not recorded"
                    rec_type = "Unrecorded"

                reply = (
                    "✅ <b>Last Blood Donation Date Updated Successfully!</b>\n\n"
                    f"• <b>Recorded Status:</b> <b>{date_display}</b>\n"
                    f"• <b>Record Type:</b> {rec_type}\n"
                    f"• <b>Availability Status:</b> Unchanged ({'Available' if updated_donor.is_available else 'Unavailable'})\n\n"
                    f"{msg}"
                )
            else:
                reply = f"❌ <b>Could Not Update Date:</b>\n\n{msg}"

            await self.client.send_message(
                chat_id=chat_id,
                text=reply,
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return
        elif data_str == "donor_date:cancel":
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text="❌ Last donation date update was cancelled. Your profile remains unchanged.",
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return
        elif data_str == "donor_up:toggle_avail":
            success, msg, new_avail = await self.service.toggle_donor_availability(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text=msg,
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return
        elif data_str == "donor_up:revoke_gps":
            await self.cmd_revokelocation(chat_id, user_id)
            return
        elif data_str == "donor_up:change_district":
            rows = []
            for i in range(0, len(KERALA_DISTRICTS), 2):
                row = [{"text": KERALA_DISTRICTS[i], "callback_data": f"donor_dist:{KERALA_DISTRICTS[i]}"}]
                if i + 1 < len(KERALA_DISTRICTS):
                    row.append({"text": KERALA_DISTRICTS[i + 1], "callback_data": f"donor_dist:{KERALA_DISTRICTS[i + 1]}"})
                rows.append(row)
            rows.append([{"text": "🔙 Back", "callback_data": "menu:update_donor_details"}])
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 Please select your updated <b>Home District</b> in Kerala:",
                reply_markup={"inline_keyboard": rows},
            )
            return
        elif data_str.startswith("donor_dist:"):
            dist_val = data_str.split(":")[1]
            success, msg = await self.service.update_donor_district(user_id, dist_val)
            await self.client.send_message(
                chat_id=chat_id,
                text=msg,
                reply_markup=self.build_main_menu_keyboard(is_donor=True),
            )
            return

        # 4b. Donor Registration Actions (Consent, Resumption, Confirmation, Edit, Cancel)
        if data_str == "reg:resume":
            conv = await self.service.get_conversation(user_id)
            if conv and conv.current_step.startswith("REG_"):
                await self.resume_registration(chat_id, user_id, conv)
            else:
                await self.start_donor_registration(chat_id, user_id)
            return
        elif data_str == "reg:cancel":
            await self.cmd_cancel(chat_id, user_id)
            return
        elif data_str == "reg:consent_no":
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text="❌ Registration cancelled. Details are only collected with your explicit consent.\nYou can return anytime via the main menu.",
                reply_markup=self.build_main_menu_keyboard(),
            )
            return
        elif data_str == "reg:consent_yes":
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_NAME",
                data_updates={"consent_recorded_at": datetime.now(timezone.utc).isoformat()},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "📝 <b>Donor Registration — Step 1 of 5: Personal Details</b>\n\n"
                    "Please enter your <b>Full Name</b> (as per official identity):\n\n"
                    "<i>Type /cancel at any point to stop.</i>"
                ),
            )
            return
        elif data_str == "reg:resend_otp":
            await self.resend_registration_otp(chat_id, user_id)
            return
        elif data_str == "reg_loc:consent_no":
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "❌ <b>Registration Cancelled:</b>\n\n"
                    "GPS location sharing and proximity consent are mandatory to register as a voluntary donor on RakthaSethu so nearby emergency patients can reach you.\n"
                    "District-only fallback registration is not permitted.\n\n"
                    "You can restart registration at any time from the main menu."
                ),
                reply_markup=self.build_main_menu_keyboard(),
            )
            return
        elif data_str == "reg_loc:consent_yes":
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_LOCATION",
                data_updates={"location_consent": True},
            )
            reply_markup = {
                "keyboard": [
                    [{"text": "📍 Share Current Location", "request_location": True}],
                    [{"text": "❌ Cancel Registration"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "📍 <b>Location Sharing (Mandatory):</b>\n\n"
                    "Please tap the <b>📍 Share Current Location</b> button below to transmit your GPS coordinates directly.\n\n"
                    "• <i>Exact coordinates are never shown to requesters.</i>\n"
                    "• <i>Typed place names cannot be accepted.</i>"
                ),
                reply_markup=reply_markup,
            )
            return
        elif data_str == "reg:edit":
            await self.client.send_message(
                chat_id=chat_id,
                text="✏️ <b>Edit Registration Details:</b>\nWhich detail would you like to update?",
                reply_markup=self.build_reg_edit_keyboard(),
            )
            return
        elif data_str.startswith("reg_edit:"):
            field = data_str.split(":")[1]
            await self.handle_registration_edit_field(chat_id, user_id, field)
            return
        elif data_str == "reg:confirm":
            conv = await self.service.get_conversation(user_id)
            conv_data = dict(conv.state_data or {}) if conv else {}
            if not conv_data.get("location_consent") or conv_data.get("latitude") is None or conv_data.get("longitude") is None:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ <b>GPS Location Mandatory:</b>\n\n"
                        "Registration cannot be submitted without valid GPS coordinates and explicit location consent.\n"
                        "Please share your location before confirming."
                    ),
                )
                return

            acquired, locked_data = await self.service.lock_and_transition_registration(user_id)
            if not acquired or not locked_data:
                logger.info("Ignoring duplicate/unlocked reg:confirm for user %s", user_id)
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⏳ Your registration is already being processed or has already been completed.",
                )
                return
            await self.submit_donor_registration(chat_id, user_id, locked_data, cb.from_user.username)
            return

        # 5. Request Confirmation / Cancel (Atomic lock & transition before state lookup)
        if data_str == "req:cancel":
            await self.cmd_cancel(chat_id, user_id)
            return
        elif data_str == "req:confirm":
            acquired, locked_data = await self.service.lock_and_transition_confirmation(user_id)
            if not acquired or not locked_data:
                logger.info("Ignoring duplicate/unlocked req:confirm for user %s", user_id)
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⏳ Your request is already being processed or has already been submitted.",
                )
                return
            await self.submit_blood_request(chat_id, user_id, locked_data, cb.from_user.username)
            return

        # 6. Check active conversation for sequential flow
        conv = await self.service.get_conversation(user_id)
        if not conv:
            return

        step = conv.current_step
        state_data = dict(conv.state_data or {})

        # Donor Registration: Blood Group Selection
        if step == "REG_BG" and data_str.startswith("reg_bg:"):
            bg_val = data_str.split(":")[1]
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_AGE",
                data_updates={"blood_group": bg_val},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"💉 Selected Blood Group: <b>{bg_val}</b>\n\n"
                    "🎂 <b>Step 3 of 5: Eligibility Check</b>\n\n"
                    "Please enter your <b>Age</b> (e.g. <code>25</code>) or <b>Date of Birth</b> (<code>YYYY-MM-DD</code>):\n\n"
                    "<i>Voluntary donors must be between 18 and 65 years old.</i>"
                ),
            )
            return

        # Donor Registration: District Selection
        if step == "REG_DISTRICT" and data_str.startswith("reg_dist:"):
            dist_val = data_str.split(":")[1]
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_PHONE_SHARE",
                data_updates={"district": dist_val},
            )
            reply_markup = {
                "keyboard": [
                    [{"text": "📱 Share Phone Number", "request_contact": True}],
                    [{"text": "❌ Cancel Registration"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"📍 District: <b>{dist_val}</b>\n\n"
                    "📱 <b>Step 4 of 5: Mobile Phone Verification</b>\n\n"
                    "Please tap the <b>📱 Share Phone Number</b> button below to share your contact directly from Telegram.\n\n"
                    "• <i>Typed numbers cannot be accepted.</i>\n"
                    "• <i>You must share the contact associated with this Telegram account.</i>"
                ),
                reply_markup=reply_markup,
            )
            return

        # 3. Blood Group Selection
        if step == "WAITING_BLOOD_GROUP" and data_str.startswith("bg:"):
            bg_val = data_str.split(":")[1]
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_UNITS",
                data_updates={"blood_group": bg_val},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"💉 Selected Blood Group: <b>{bg_val}</b>\n\n🔢 <b>Step 3 of 8:</b> Select the number of <b>Units Required</b>:",
                reply_markup=self.build_units_keyboard(),
            )
            return

        # 4. Units Selection
        if step == "WAITING_UNITS" and data_str.startswith("units:"):
            units_val = int(data_str.split(":")[1])
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_DISTRICT",
                data_updates={"units_requested": units_val},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"🔢 Units: <b>{units_val}</b>\n\n📍 <b>Step 4 of 8:</b> Select the <b>Target District</b> in Kerala:",
                reply_markup=self.build_district_keyboard(),
            )
            return

        # 5. District Selection
        if step == "WAITING_DISTRICT" and data_str.startswith("dist:"):
            district_val = data_str.split(":")[1]
            # Fetch active hospitals for this district
            hosp_repo = HospitalRepository(self.session)
            hospitals = await hosp_repo.list_active_by_district(district_val)

            if not hospitals:
                # Inform requester no partner hospital exists in this district
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⚠️ <b>No Registered Partner Hospitals in {district_val}</b>\n\n"
                        f"Currently, there are no verified partner hospitals registered in {district_val} on the RakthaSethu network.\n\n"
                        f"• Please contact your nearest district hospital blood bank directly, or\n"
                        f"• Select an adjacent district where partner facilities are active."
                    ),
                    reply_markup=self.build_district_keyboard(),
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_HOSPITAL",
                data_updates={"district": district_val},
            )

            # Build hospital keyboard
            buttons = []
            for h in hospitals:
                buttons.append([{"text": f"🏥 {h.name}", "callback_data": f"hosp:{h.id}"}])
            kb = {"inline_keyboard": buttons}

            await self.client.send_message(
                chat_id=chat_id,
                text=f"📍 District: <b>{district_val}</b>\n\n🏥 <b>Step 5 of 8:</b> Select the <b>Requesting Hospital</b>:",
                reply_markup=kb,
            )
            return

        # 6. Hospital Selection
        if step == "WAITING_HOSPITAL" and data_str.startswith("hosp:"):
            hosp_id = int(data_str.split(":")[1])
            hosp_repo = HospitalRepository(self.session)
            hospital = await hosp_repo.get_by_id(hosp_id)
            if not hospital or not hospital.is_active:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Selected hospital is currently inactive or unavailable. Please choose another facility.",
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_DATE",
                data_updates={"hospital_id": hosp_id, "hospital_name": hospital.name},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"🏥 Hospital: <b>{hospital.name}</b>\n\n"
                    f"📅 <b>Step 6 of 8:</b> When is the blood needed? Choose a quick date or type <code>YYYY-MM-DD</code>:"
                ),
                reply_markup=self.build_date_keyboard(),
            )
            return

        # 7. Date Selection
        if step == "WAITING_DATE" and data_str.startswith("date:"):
            days_offset = int(data_str.split(":")[1])
            target_date = date.today() + timedelta(days=days_offset)
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="WAITING_PHONE",
                data_updates={"required_date": target_date.isoformat()},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"📅 Target Date: <b>{target_date.isoformat()}</b>\n\n📞 <b>Step 7 of 8:</b> Enter the <b>Contact Phone Number</b> for coordination:",
            )
            return

        # 8. Urgency Selection
        if step == "WAITING_URGENCY" and data_str.startswith("urg:"):
            urgency_val = data_str.split(":")[1]
            state_data["urgency"] = urgency_val

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="CONFIRMATION",
                data_updates={"urgency": urgency_val},
            )

            # Build confirmation summary
            summary = (
                "📋 <b>Please Confirm Your Blood Request</b>\n\n"
                f"• <b>Patient:</b> {state_data.get('patient_name')}\n"
                f"• <b>Blood Group:</b> {state_data.get('blood_group')}\n"
                f"• <b>Units:</b> {state_data.get('units_requested')}\n"
                f"• <b>District:</b> {state_data.get('district')}\n"
                f"• <b>Hospital:</b> {state_data.get('hospital_name')}\n"
                f"• <b>Target Date:</b> {state_data.get('required_date')}\n"
                f"• <b>Contact:</b> {state_data.get('contact_phone')}\n"
                f"• <b>Urgency:</b> {urgency_val}\n\n"
                "<i>Ready to dispatch to the hospital network?</i>"
            )
            kb = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Confirm & Submit", "callback_data": "req:confirm"},
                        {"text": "❌ Cancel", "callback_data": "req:cancel"},
                    ]
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=summary, reply_markup=kb)
            return


    async def submit_blood_request(
        self,
        chat_id: int,
        user_id: int,
        data: Dict[str, Any],
        username: Optional[str],
    ) -> None:
        try:
            # 1. Hospital validation: ensure hospital exists and is active
            hosp_id = int(data["hospital_id"])
            hosp_repo = HospitalRepository(self.session)
            hospital = await hosp_repo.get_by_id(hosp_id)
            if not hospital or not hospital.is_active:
                await self.service.reset_conversation(user_id)
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ The selected hospital is inactive or unavailable. Please restart your request with /requestblood.",
                )
                return

            # 2. Construct validated domain schema
            req_dto = BloodRequestCreate(
                hospital_id=hosp_id,
                patient_name=str(data["patient_name"]),
                blood_group=BloodGroup(data["blood_group"]),
                units_requested=int(data["units_requested"]),
                district=str(data["district"]),
                location=str(data.get("district")),
                contact_phone=str(data["contact_phone"]),
                required_date=date.fromisoformat(data["required_date"]),
                urgency=RequestUrgency(data["urgency"]),
                status=RequestStatus.PENDING,
            )

            service = BloodRequestService(self.session)
            created_req = await service.create_blood_request(req_dto)

            # 3. Record private ownership binding in database
            await self.service.record_telegram_blood_request(
                blood_request_id=created_req.id,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                telegram_username=username,
            )

            # 4. Reset conversation state
            await self.service.reset_conversation(user_id)

            # 5. Format and display nearest-donor ranking view (never show matches before save)
            text, reply_markup = await self.format_donor_matches_view(
                req_id=created_req.id,
                user_id=user_id,
                page=1,
                radius_km=settings.DEFAULT_PROXIMITY_RADIUS_KM,
                is_initial=True,
            )

            await self.client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
            )
        except Exception as exc:
            logger.exception("Failed to submit blood request from Telegram: %s", exc)
            await self.client.send_message(
                chat_id=chat_id,
                text=f"⚠️ Failed to submit request: {exc}. Please type /cancel and try again.",
            )

    def _format_donor_contact(self, donor_item: Any) -> str:
        """
        Formats donor contact phone number for eligible matches:
        - If a valid phone number exists in the donor record: displays the normalized phone number.
        - If a phone number is absent or invalid: displays 'Contact the registered hospital for assistance.'
        """
        phone_raw = getattr(donor_item, "phone", None)
        if phone_raw and str(phone_raw).strip():
            try:
                norm_phone = normalize_phone_number(str(phone_raw).strip())
                return f"<code>{norm_phone}</code>"
            except Exception:
                return "Contact the registered hospital for assistance."
        return "Contact the registered hospital for assistance."

    async def format_donor_matches_view(
        self,
        req_id: int,
        user_id: int,
        page: int = 1,
        radius_km: float = 25.0,
        is_initial: bool = False,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Formats a privacy-preserving summary of potential matching donors,
        ranked nearest first using PostGIS proximity queries.
        Displays donor reference code, blood group, approximate distance, and contact phone number.
        Never reveals donor full names, exact coordinates, street addresses, or internal database IDs.
        """
        is_auth, is_staff, req, hosp = await self.service.verify_request_access_by_id(req_id, user_id)
        if not req:
            return "⚠️ Blood request not found.", None
        if not is_auth:
            return "⛔ <b>Access Denied:</b> You are not authorized to view matches for this blood request.", None

        hosp_name = hosp.name if hosp else (req.hospital.name if req.hospital else "Assigned Hospital")
        hosp_has_location = (
            hosp is not None
            and hosp.latitude is not None
            and hosp.longitude is not None
        )

        safe_radius_km = min(max(1.0, float(radius_km)), settings.MAX_PROXIMITY_RADIUS_KM)

        matching_service = MatchingService(self.session)
        from app.schemas.matching import MatchDonorsRequest

        match_req = MatchDonorsRequest(
            blood_group=req.blood_group,
            district=req.district,
            hospital_id=req.hospital_id,
            radius_km=safe_radius_km,
            required_units=req.units_requested,
            required_date=req.required_date,
            limit=settings.MAX_MATCH_LIMIT,
            include_fallback=True,
        )

        try:
            match_result = await matching_service.find_matching_donors(match_req)
        except Exception as exc:
            logger.error("Matching calculation error for req_id=%s: %s", req_id, exc)
            fallback_text = (
                f"🩸 <b>Blood Request Registered</b>\n\n"
                f"📌 <b>Request ID:</b> <code>{req.request_code}</code>\n"
                f"🏥 <b>Hospital:</b> {hosp_name}\n"
                f"💉 <b>Blood Group:</b> {req.blood_group.value} ({req.units_requested} Unit{'s' if req.units_requested > 1 else ''})\n\n"
                f"Your request has been logged with the hospital network. Matching donors could not be calculated at this time.\n\n"
                f"Check status anytime: <code>/status {req.request_code}</code>"
            )
            return fallback_text, self.build_main_menu_keyboard()

        # Build Title / Header
        if is_initial:
            header = (
                "🩸 <b>Blood Request Registered</b>\n\n"
                f"📌 <b>Request ID:</b> <code>{req.request_code}</code>\n"
                f"🏥 <b>Hospital:</b> {hosp_name}\n"
                f"💉 <b>Blood Group:</b> {req.blood_group.value} ({req.units_requested} Unit{'s' if req.units_requested > 1 else ''})\n\n"
            )
        else:
            header = (
                f"📍 <b>Nearest Potential Donors for #{req.request_code}</b>\n\n"
                f"🏥 <b>Hospital:</b> {hosp_name}\n"
                f"💉 <b>Blood Group:</b> {req.blood_group.value} ({req.units_requested} Unit{'s' if req.units_requested > 1 else ''})\n\n"
            )

        if not hosp_has_location or match_result.origin_type == "DISTRICT_DEFAULT":
            header += "📍 <i>Note: Hospital coordinates are unavailable. Displaying district-level matches.</i>\n\n"

        # Case A: 0 matches found
        if match_result.total_eligible_found == 0:
            radius_desc = f"within {int(safe_radius_km)} km of {hosp_name}" if hosp_has_location else f"in {req.district}"
            body = (
                f"We searched {radius_desc}, but found no potential matching donors at this time.\n\n"
                f"<b>Next Steps:</b>\n"
                f"• Contact {hosp_name} directly to explore reserve inventory or regional blood bank transfers.\n"
                f"• Broaden the search radius using the button below if appropriate.\n"
                f"• Check your request status anytime with: <code>/status {req.request_code}</code>\n\n"
                f"<i>These are potential matches, not confirmed availability.</i>"
            )

            kb_rows = []
            if hosp_has_location:
                if safe_radius_km < 50.0 and 50.0 <= settings.MAX_PROXIMITY_RADIUS_KM:
                    kb_rows.append([{"text": "🔍 Broaden Search to 50 km", "callback_data": f"match:r:{req.id}:50"}])
                elif safe_radius_km < 100.0 and 100.0 <= settings.MAX_PROXIMITY_RADIUS_KM:
                    kb_rows.append([{"text": "🔍 Broaden Search to 100 km", "callback_data": f"match:r:{req.id}:100"}])

            kb_rows.append([{"text": "📊 Check Status", "callback_data": "menu:status"}])
            kb_rows.append([{"text": "🏠 Main Menu", "callback_data": "menu:help"}])
            return header + body, {"inline_keyboard": kb_rows}

        # Case B: Potential matches found
        PAGE_SIZE = 5
        items = match_result.items
        total_items = len(items)
        total_pages = max(1, math.ceil(total_items / PAGE_SIZE))
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_items = items[start_idx:end_idx]

        match_count = match_result.total_eligible_found
        match_word = "potential match" if match_count == 1 else "potential matches"
        radius_info = f" within {int(safe_radius_km)} km" if (hosp_has_location and match_result.origin_type != "DISTRICT_DEFAULT") else ""

        body = f"We found {match_count} {match_word}{radius_info}, ranked by proximity:\n\n"

        for i, d in enumerate(page_items):
            rank = start_idx + i + 1
            if d.distance_km is not None:
                dist_str = f"approximately {d.distance_km} km away"
            else:
                dist_str = f"Distance unknown (district match: {d.district})"

            contact_str = self._format_donor_contact(d)

            body += (
                f"<b>Potential donor {rank}</b>\n"
                f"- Donor reference: <code>{d.donor_code}</code>\n"
                f"- Blood group: {d.blood_group.value}\n"
                f"- Distance: {dist_str}\n"
                f"- Contact: {contact_str}\n\n"
            )

        body += (
            "<i>These are potential matches, not confirmed availability. "
            "Please verify availability before coordinating a donation. "
            "Contact the registered hospital or authorized staff to confirm donor availability and coordinate donation.</i>"
        )

        kb_rows = []
        # Pagination row
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append({"text": "◀ Prev", "callback_data": f"match:p:{req.id}:{page - 1}:{int(safe_radius_km)}"})
            nav_buttons.append({"text": f"{page} / {total_pages}", "callback_data": "noop"})
            if page < total_pages:
                nav_buttons.append({"text": "Next ▶", "callback_data": f"match:p:{req.id}:{page + 1}:{int(safe_radius_km)}"})
            kb_rows.append(nav_buttons)

        # Radius expansion row
        if hosp_has_location and match_result.origin_type != "DISTRICT_DEFAULT":
            if safe_radius_km < 50.0 and 50.0 <= settings.MAX_PROXIMITY_RADIUS_KM:
                kb_rows.append([{"text": "🔍 Expand Radius to 50 km", "callback_data": f"match:r:{req.id}:50"}])
            elif safe_radius_km < 100.0 and 100.0 <= settings.MAX_PROXIMITY_RADIUS_KM:
                kb_rows.append([{"text": "🔍 Expand Radius to 100 km", "callback_data": f"match:r:{req.id}:100"}])

        # Authorized staff portal view
        if is_staff:
            kb_rows.append([{"text": "🏥 Staff Outreach View", "callback_data": f"staff_match:{req.id}"}])

        return header + body, {"inline_keyboard": kb_rows}

    async def handle_donor_match_page(
        self,
        chat_id: int,
        user_id: int,
        cb: TelegramCallbackQuery,
    ) -> None:
        """
        Handles pagination and radius broadening callbacks securely:
        - match:p:<req_id>:<page>:<radius>
        - match:r:<req_id>:<radius>
        Revalidates request ownership and radius constraints on every callback.
        """
        data_str = cb.data or ""
        try:
            parts = data_str.split(":")
            if parts[1] == "p" and len(parts) >= 5:
                req_id = int(parts[2])
                page = int(parts[3])
                radius_km = float(parts[4])
            elif parts[1] == "r" and len(parts) >= 4:
                req_id = int(parts[2])
                page = 1
                radius_km = float(parts[3])
            else:
                logger.warning("Invalid match callback format: %s", data_str)
                return
        except (ValueError, IndexError) as err:
            logger.warning("Failed to parse match callback %s: %s", data_str, err)
            return

        if not math.isfinite(radius_km) or radius_km <= 0 or radius_km > settings.MAX_PROXIMITY_RADIUS_KM:
            logger.warning("Rejected invalid radius_km in callback: %s", radius_km)
            return

        if page < 1:
            page = 1

        is_auth, is_staff, req, hosp = await self.service.verify_request_access_by_id(req_id, user_id)
        if not req:
            await self.client.send_message(
                chat_id=chat_id,
                text="⚠️ Blood request not found.",
            )
            return

        if not is_auth:
            await self.client.send_message(
                chat_id=chat_id,
                text="⛔ <b>Access Denied:</b> You are not authorized to view matches for this blood request.",
            )
            return

        text, reply_markup = await self.format_donor_matches_view(
            req_id=req_id,
            user_id=user_id,
            page=page,
            radius_km=radius_km,
            is_initial=False,
        )

        if cb.message:
            res = await self.client.edit_message_text(
                chat_id=chat_id,
                message_id=cb.message.message_id,
                text=text,
                reply_markup=reply_markup,
            )
            if not res.get("ok"):
                # Fallback to new message if edit fails (e.g. text unmodified)
                pass
        else:
            await self.client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
            )

    async def handle_staff_match_view(self, chat_id: int, user_id: int, req_id: int) -> None:
        linked_staff = await self.service.get_linked_staff(user_id)
        if not linked_staff or not linked_staff.is_active or not linked_staff.user:
            await self.client.send_message(chat_id=chat_id, text="⛔ Unauthorized.")
            return

        user = linked_staff.user
        req_service = BloodRequestService(self.session)
        req = await req_service.get_blood_request_by_id(req_id)
        if not req:
            await self.client.send_message(chat_id=chat_id, text="Request not found.")
            return

        # Hospital scope check
        if user.role != UserRole.SUPER_ADMIN and user.hospital_id != req.hospital_id:
            await self.client.send_message(chat_id=chat_id, text="⛔ Hospital access denied.")
            return

        matching_service = MatchingService(self.session)
        from app.schemas.matching import MatchDonorsRequest
        match_req = MatchDonorsRequest(
            blood_group=req.blood_group,
            district=req.district,
            hospital_id=req.hospital_id,
            required_units=req.units_requested,
            required_date=req.required_date,
            limit=10,
        )
        match_result = await matching_service.find_matching_donors(match_req)

        res_text = (
            f"🔍 <b>Matching Donors for #{req.request_code}</b>\n\n"
            f"• <b>Total Eligible Found:</b> {match_result.total_eligible_found}\n"
            f"• <b>Compatible Groups:</b> {', '.join(g.value for g in match_result.compatible_blood_groups)}\n"
            f"• <b>Search Origin:</b> {match_result.origin_type}\n\n"
        )
        if match_result.items:
            res_text += "<b>Top Eligible Candidates:</b>\n"
            for idx, d in enumerate(match_result.items[:5], 1):
                dist_str = f"{d.distance_km} km" if d.distance_km is not None else "District Fallback"
                res_text += f"{idx}. <b>{d.donor_code}</b> ({d.blood_group.value}) — {dist_str}\n"
            res_text += "\n<i>Full contact details and outreach dispatch are managed in the hospital web portal.</i>"
        else:
            res_text += "No active eligible donors found within current radius."

        await self.client.send_message(chat_id=chat_id, text=res_text)

    # ─── Keyboard Builders ────────────────────────────────────────────────

    def build_main_menu_keyboard(self, is_donor: bool = False) -> Dict[str, Any]:
        if is_donor:
            return {
                "inline_keyboard": [
                    [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                    [{"text": "👤 View My Donor Profile", "callback_data": "menu:view_donor_profile"}],
                    [{"text": "✏️ Update My Details", "callback_data": "menu:update_donor_details"}],
                    [{"text": "🔍 Check Request Status", "callback_data": "menu:status"}],
                    [
                        {"text": "🏥 Staff Link", "callback_data": "menu:link"},
                        {"text": "ℹ️ Help", "callback_data": "menu:help"},
                    ],
                ]
            }
        return {
            "inline_keyboard": [
                [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                [{"text": "📝 Register as Donor", "callback_data": "menu:register_donor"}],
                [{"text": "🔍 Check Request Status", "callback_data": "menu:status"}],
                [
                    {"text": "🏥 Staff Link", "callback_data": "menu:link"},
                    {"text": "ℹ️ Help", "callback_data": "menu:help"},
                ],
            ]
        }

    def build_reg_blood_group_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "A+", "callback_data": "reg_bg:A+"}, {"text": "A-", "callback_data": "reg_bg:A-"}],
                [{"text": "B+", "callback_data": "reg_bg:B+"}, {"text": "B-", "callback_data": "reg_bg:B-"}],
                [{"text": "AB+", "callback_data": "reg_bg:AB+"}, {"text": "AB-", "callback_data": "reg_bg:AB-"}],
                [{"text": "O+", "callback_data": "reg_bg:O+"}, {"text": "O-", "callback_data": "reg_bg:O-"}],
            ]
        }

    def build_reg_district_keyboard(self) -> Dict[str, Any]:
        rows = []
        for i in range(0, len(KERALA_DISTRICTS), 2):
            row = [{"text": KERALA_DISTRICTS[i], "callback_data": f"reg_dist:{KERALA_DISTRICTS[i]}"}]
            if i + 1 < len(KERALA_DISTRICTS):
                row.append({"text": KERALA_DISTRICTS[i + 1], "callback_data": f"reg_dist:{KERALA_DISTRICTS[i + 1]}"})
            rows.append(row)
        return {"inline_keyboard": rows}

    def build_reg_edit_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "👤 Edit Name", "callback_data": "reg_edit:name"}],
                [{"text": "💉 Edit Blood Group", "callback_data": "reg_edit:bg"}],
                [{"text": "🎂 Edit Age / DOB", "callback_data": "reg_edit:age"}],
                [{"text": "📍 Edit District", "callback_data": "reg_edit:dist"}],
                [{"text": "🗺️ Edit Location", "callback_data": "reg_edit:loc"}],
                [{"text": "🔙 Back to Summary", "callback_data": "reg_edit:back"}],
            ]
        }

    def _mask_phone(self, phone: str) -> str:
        clean = str(phone).strip()
        if len(clean) >= 10:
            return clean[:5] + "****" + clean[-4:]
        return clean

    def _parse_age_or_dob(self, text: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        raw = text.strip()
        # Case A: Pure integer age
        if raw.isdigit():
            age = int(raw)
            if age < 18:
                return None, None, "⚠️ You must be at least 18 years old to register as a voluntary blood donor under National Blood Transfusion Council (NBTC) guidelines. Please re-enter if this was an error:"
            if age > 65:
                return None, None, "⚠️ Voluntary blood donation is recommended up to 65 years of age. Please re-enter if this was an error:"
            return age, None, None

        # Case B: Date of Birth
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue

        if not parsed_date:
            return None, None, "⚠️ Please enter your age (e.g. <code>25</code>) or Date of Birth (<code>YYYY-MM-DD</code>):"

        today = date.today()
        if parsed_date > today:
            return None, None, "⚠️ Date of birth cannot be in the future. Please re-enter:"

        age = today.year - parsed_date.year - ((today.month, today.day) < (parsed_date.month, parsed_date.day))
        if age < 18:
            return None, None, "⚠️ You must be at least 18 years old to register as a voluntary blood donor under National Blood Transfusion Council (NBTC) guidelines. Please re-enter if this was an error:"
        if age > 65:
            return None, None, "⚠️ Voluntary blood donation is recommended up to 65 years of age. Please re-enter if this was an error:"

        return age, parsed_date.isoformat(), None

    async def handle_registration_edit_field(self, chat_id: int, user_id: int, field: str) -> None:
        conv = await self.service.get_conversation(user_id)
        if not conv:
            return

        if field == "name":
            await self.service.update_conversation(user_id, chat_id, "REG_NAME")
            await self.client.send_message(chat_id=chat_id, text="👤 Please enter your updated <b>Full Name</b>:")
        elif field == "bg":
            await self.service.update_conversation(user_id, chat_id, "REG_BG")
            await self.client.send_message(
                chat_id=chat_id,
                text="💉 Please select your updated <b>Blood Group</b>:",
                reply_markup=self.build_reg_blood_group_keyboard(),
            )
        elif field == "age":
            await self.service.update_conversation(user_id, chat_id, "REG_AGE")
            await self.client.send_message(chat_id=chat_id, text="🎂 Please enter your updated <b>Age</b> (18–65) or Date of Birth:")
        elif field == "dist":
            await self.service.update_conversation(user_id, chat_id, "REG_DISTRICT")
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 Please select your updated <b>Home District</b>:",
                reply_markup=self.build_reg_district_keyboard(),
            )
        elif field == "loc":
            await self.service.update_conversation(user_id, chat_id, "REG_LOC_CONSENT")
            kb = {
                "inline_keyboard": [
                    [{"text": "📍 I Consent & Share Location", "callback_data": "reg_loc:consent_yes"}],
                    [{"text": "❌ Decline & Cancel", "callback_data": "reg_loc:consent_no"}],
                ]
            }
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 Do you consent to sharing your GPS location for emergency proximity matching? (Mandatory for voluntary donor registration)",
                reply_markup=kb,
            )
        elif field == "back":
            await self.service.update_conversation(user_id, chat_id, "REG_CONFIRM")
            await self.send_registration_summary(chat_id, user_id, conv)

    async def resend_registration_otp(self, chat_id: int, user_id: int) -> None:
        conv = await self.service.get_conversation(user_id)
        if not conv or conv.current_step != "REG_OTP":
            return

        state_data = dict(conv.state_data or {})
        sent_at_str = state_data.get("otp_sent_at")
        now = datetime.now(timezone.utc)
        if sent_at_str:
            sent_dt = datetime.fromisoformat(sent_at_str)
            elapsed = (now - sent_dt).total_seconds()
            if elapsed < 60:
                wait_sec = int(60 - elapsed)
                await self.client.send_message(
                    chat_id=chat_id,
                    text=f"⏳ Please wait {wait_sec} seconds before requesting a new verification code.",
                )
                return

        new_otp = f"{secrets.randbelow(900000) + 100000:06d}"
        new_hash = hashlib.sha256(new_otp.encode("utf-8")).hexdigest()

        await self.service.update_conversation(
            telegram_user_id=user_id,
            chat_id=chat_id,
            step="REG_OTP",
            data_updates={
                "otp_hash": new_hash,
                "otp_sent_at": now.isoformat(),
                "otp_expires_at": (now + timedelta(minutes=10)).isoformat(),
                "otp_attempts": 0,
            },
        )
        msg = (
            f"🔄 <b>New Telegram Verification Code:</b> <code>{new_otp}</code>\n\n"
            "Please enter this 6-digit code to complete verification.\n"
            "• <i>Code expires in 10 minutes.</i>"
        )
        await self.client.send_message(chat_id=chat_id, text=msg)

    async def resume_registration(self, chat_id: int, user_id: int, conv: Any) -> None:
        step = conv.current_step
        if step == "REG_CONSENT":
            await self.start_donor_registration(chat_id, user_id)
        elif step == "REG_NAME":
            await self.client.send_message(
                chat_id=chat_id,
                text="📝 <b>Donor Registration — Step 1 of 5:</b>\nPlease enter your <b>Full Name</b>:\n<i>Type /cancel to abort.</i>",
            )
        elif step == "REG_BG":
            await self.client.send_message(
                chat_id=chat_id,
                text="💉 <b>Step 2 of 5:</b> Please select your <b>Blood Group</b>:",
                reply_markup=self.build_reg_blood_group_keyboard(),
            )
        elif step == "REG_AGE":
            await self.client.send_message(
                chat_id=chat_id,
                text="🎂 <b>Step 3 of 5:</b> Please enter your <b>Age</b> (18–65) or Date of Birth (<code>YYYY-MM-DD</code>):",
            )
        elif step == "REG_DISTRICT":
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 <b>Step 4 of 5:</b> Please select your <b>Home District</b> in Kerala:",
                reply_markup=self.build_reg_district_keyboard(),
            )
        elif step == "REG_PHONE_SHARE":
            reply_markup = {
                "keyboard": [
                    [{"text": "📱 Share Phone Number", "request_contact": True}],
                    [{"text": "❌ Cancel Registration"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "📱 <b>Phone Verification:</b>\n"
                    "Please tap the <b>📱 Share Phone Number</b> button below to share your contact directly from Telegram."
                ),
                reply_markup=reply_markup,
            )
        elif step == "REG_OTP":
            await self.client.send_message(
                chat_id=chat_id,
                text="🔐 Please enter the 6-digit verification code sent in this chat (or type /resend for a new code):",
            )
        elif step == "REG_LOC_CONSENT":
            kb = {
                "inline_keyboard": [
                    [{"text": "📍 I Consent & Share Location", "callback_data": "reg_loc:consent_yes"}],
                    [{"text": "❌ Decline & Cancel", "callback_data": "reg_loc:consent_no"}],
                ]
            }
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 Do you consent to sharing your GPS location for emergency proximity matching? (Mandatory for registration)",
                reply_markup=kb,
            )
        elif step == "REG_LOCATION":
            reply_markup = {
                "keyboard": [
                    [{"text": "📍 Share Current Location", "request_location": True}],
                    [{"text": "❌ Cancel Registration"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
            await self.client.send_message(
                chat_id=chat_id,
                text="📍 Please tap <b>Share Current Location</b> below to share your GPS coordinates (Mandatory):",
                reply_markup=reply_markup,
            )
        elif step == "REG_CONFIRM":
            await self.send_registration_summary(chat_id, user_id, conv)
        else:
            await self.start_donor_registration(chat_id, user_id)

    async def send_registration_summary(self, chat_id: int, user_id: int, conv: Any) -> None:
        data = dict(conv.state_data or {})
        masked_phone = self._mask_phone(data.get("phone", "Unknown"))
        has_loc = data.get("location_consent") and data.get("latitude") is not None
        loc_desc = "✅ Coordinates Received (GPS Proximity Enabled)" if has_loc else "⏭️ Skipped (District Matching Only)"

        summary_text = (
            "📋 <b>Donor Registration Summary</b>\n\n"
            f"👤 <b>Full Name:</b> {data.get('full_name')}\n"
            f"💉 <b>Blood Group:</b> <b>{data.get('blood_group')}</b>\n"
            f"🎂 <b>Age:</b> {data.get('age')} years\n"
            f"📍 <b>District:</b> {data.get('district')}\n"
            f"📱 <b>Phone:</b> <code>{masked_phone}</code> (Verified)\n"
            f"🗺️ <b>Location:</b> {loc_desc}\n\n"
            "Please review your details carefully before confirming submission."
        )
        kb = {
            "inline_keyboard": [
                [{"text": "✅ Confirm & Complete Registration", "callback_data": "reg:confirm"}],
                [{"text": "✏️ Edit Details", "callback_data": "reg:edit"}],
                [{"text": "❌ Cancel", "callback_data": "reg:cancel"}],
            ]
        }
        await self.client.send_message(chat_id=chat_id, text=summary_text, reply_markup=kb)

    async def submit_donor_registration(
        self, chat_id: int, user_id: int, state_data: Dict[str, Any], username: Optional[str]
    ) -> None:
        try:
            status, result = await self.service.save_registered_donor(
                telegram_user_id=user_id,
                chat_id=chat_id,
                username=username,
                data=state_data,
            )

            if status == "CREATED":
                donor = result
                reply_text = (
                    "🎉 <b>Voluntary Donor Registration Successful!</b>\n\n"
                    f"Welcome to the RakthaSethu network, <b>{donor.full_name}</b>!\n\n"
                    f"• <b>Donor Code:</b> <code>{donor.donor_code}</code>\n"
                    f"• <b>Blood Group:</b> {donor.blood_group.value}\n"
                    f"• <b>District:</b> {donor.district}\n"
                    f"• <b>Status:</b> Active & Available for Clinical Matching\n\n"
                    "Thank you for volunteering to save lives. When a compatible clinical blood request "
                    "is submitted in your area, you may be contacted by authorized hospital coordinators.\n\n"
                    "<i>You can revoke location consent at any time by typing /revokelocation.</i>"
                )
            elif status == "UPDATED":
                donor = result
                reply_text = (
                    "✅ <b>Donor Profile Updated & Linked!</b>\n\n"
                    f"Welcome back, <b>{donor.full_name}</b>!\n\n"
                    f"• <b>Donor Code:</b> <code>{donor.donor_code}</code>\n"
                    f"• <b>Blood Group:</b> {donor.blood_group.value}\n"
                    f"• <b>District:</b> {donor.district}\n"
                    f"• <b>Status:</b> Active & Available\n\n"
                    "Your voluntary donor profile is now linked to this Telegram account."
                )
            elif status == "ALREADY_REGISTERED":
                donor = result
                reply_text = (
                    "✅ <b>Already Registered as Donor:</b>\n\n"
                    f"You are already registered in the RakthaSethu network as <b>{donor.full_name}</b> "
                    f"(Donor Code: <code>{donor.donor_code}</code>, {donor.blood_group.value}).\n\n"
                    "You do not need to register again."
                )
            elif status == "REVIEW_CASE":
                case = result
                case_id = getattr(case, "id", None) or (case.get("case_id") if isinstance(case, dict) else "PENDING")
                reply_text = (
                    "ℹ️ <b>Registration Submitted for Administrative Review</b>\n\n"
                    "A donor profile with this phone number is already registered under differing details. "
                    "To safeguard donor identity and prevent unauthorized record overwriting, an administrative review case has been recorded.\n\n"
                    f"• <b>Review Case ID:</b> <code>CASE-{case_id}</code>\n"
                    "• <b>Status:</b> Pending Hospital Desk Verification\n\n"
                    "Our hospital coordination team will review the submitted details. "
                    "Thank you for your patience and willingness to donate."
                )
            else:
                reply_text = "✅ Registration processed successfully."

            is_donor = status in ("CREATED", "UPDATED", "ALREADY_REGISTERED")
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text=reply_text,
                reply_markup=self.build_main_menu_keyboard(is_donor=is_donor),
            )
        except Exception as exc:
            logger.exception("Error during donor registration submission: %s", exc)
            await self.service.reset_conversation(user_id)
            await self.client.send_message(
                chat_id=chat_id,
                text="⚠️ An unexpected error occurred while saving your registration. Please try again with /registerdonor.",
                reply_markup=self.build_main_menu_keyboard(),
            )

    async def handle_registration_step(
        self,
        conv: Any,
        message: TelegramMessage,
        chat_id: int,
        user_id: int,
    ) -> None:
        step = conv.current_step
        text = (message.text or "").strip()

        if text.startswith("/cancel") or text in ("❌ Cancel Registration", "❌ Cancel"):
            await self.cmd_cancel(chat_id, user_id)
            return

        if step == "REG_NAME":
            name = text.strip()
            if len(name) < 2 or len(name) > 150 or not re.match(r"^[a-zA-Z\s\.\-']+$", name):
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Please enter a valid name (2 to 150 characters, letters only). Please re-enter:",
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_BG",
                data_updates={"full_name": name},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"👤 Name: <b>{name}</b>\n\n💉 <b>Step 2 of 5:</b> Select your <b>Blood Group</b>:",
                reply_markup=self.build_reg_blood_group_keyboard(),
            )

        elif step == "REG_AGE":
            age, dob, err = self._parse_age_or_dob(text)
            if err:
                await self.client.send_message(chat_id=chat_id, text=err)
                return

            data_up = {"age": age}
            if dob:
                data_up["dob"] = dob

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_DISTRICT",
                data_updates=data_up,
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=f"🎂 Age: <b>{age} years</b>\n\n📍 <b>Step 3 of 5:</b> Select your <b>Home District</b> in Kerala:",
                reply_markup=self.build_reg_district_keyboard(),
            )

        elif step == "REG_PHONE_SHARE":
            if not message.contact:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ <b>Native Verification Required:</b>\n"
                        "Typed phone numbers cannot be verified. Please tap the native <b>📱 Share Phone Number</b> button below to share your contact directly."
                    ),
                    reply_markup={
                        "keyboard": [
                            [{"text": "📱 Share Phone Number", "request_contact": True}],
                            [{"text": "❌ Cancel Registration"}]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True,
                    },
                )
                return

            # Verify contact belongs to the Telegram account interacting with the bot
            if message.contact.user_id != user_id:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        "⛔ <b>Security Check Failed:</b>\n"
                        "The shared contact does not match this Telegram account. You may only register using your own phone number.\n"
                        "Please use the <b>📱 Share Phone Number</b> button below."
                    ),
                )
                return

            try:
                norm_phone = normalize_phone_number(message.contact.phone_number)
            except Exception:
                norm_phone = message.contact.phone_number.strip()

            # Generate secure one-time verification code
            otp = f"{secrets.randbelow(900000) + 100000:06d}"
            otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
            now = datetime.now(timezone.utc)

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_OTP",
                data_updates={
                    "phone": norm_phone,
                    "otp_hash": otp_hash,
                    "otp_sent_at": now.isoformat(),
                    "otp_expires_at": (now + timedelta(minutes=10)).isoformat(),
                    "otp_attempts": 0,
                },
            )

            # Send OTP through Telegram bot chat (Never log OTP)
            otp_msg = (
                f"🔐 <b>Telegram Verification Code:</b> <code>{otp}</code>\n\n"
                "Please enter this 6-digit code below to confirm control of this Telegram chat session.\n\n"
                "• <i>This code expires in 10 minutes.</i>\n"
                "• <i>(This code is delivered through Telegram to confirm bot conversation control; it is not independent proof of mobile-network ownership.)</i>"
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=otp_msg,
                reply_markup={"remove_keyboard": True},
            )

        elif step == "REG_OTP":
            if text.startswith("/resend"):
                await self.resend_registration_otp(chat_id, user_id)
                return

            state_data = dict(conv.state_data or {})
            otp_hash = state_data.get("otp_hash")
            expires_at_str = state_data.get("otp_expires_at")
            attempts = state_data.get("otp_attempts", 0)

            now = datetime.now(timezone.utc)
            if expires_at_str:
                exp_dt = datetime.fromisoformat(expires_at_str)
                if now > exp_dt:
                    await self.client.send_message(
                        chat_id=chat_id,
                        text="⚠️ Verification code expired. Please type /resend to receive a new code or /cancel to abort.",
                    )
                    return

            if attempts >= 3:
                await self.client.send_message(
                    chat_id=chat_id,
                    text="❌ Maximum verification attempts exceeded. Please type /resend to receive a fresh code or /cancel to abort.",
                )
                return

            entered_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if entered_hash != otp_hash:
                new_attempts = attempts + 1
                remaining = max(0, 3 - new_attempts)
                await self.service.update_conversation(
                    telegram_user_id=user_id,
                    chat_id=chat_id,
                    step="REG_OTP",
                    data_updates={"otp_attempts": new_attempts},
                )
                await self.client.send_message(
                    chat_id=chat_id,
                    text=f"❌ Incorrect verification code. You have {remaining} attempt(s) remaining. Please try again or type /resend:",
                )
                return

            # OTP verified successfully!
            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_LOC_CONSENT",
                data_updates={"phone_verified": True, "otp_hash": None},
            )

            loc_consent_text = (
                "📍 <b>Step 5 of 5: Proximity Matching & Location Consent</b>\n\n"
                "RakthaSethu uses GPS proximity matching to connect emergency patients with the nearest available voluntary donors across Kerala.\n\n"
                "<b>Privacy & Security Safeguards:</b>\n"
                "• Your exact coordinates are <b>never disclosed</b> to requesters or arbitrary users.\n"
                "• Only approximate straight-line distance (e.g. '4.5 km') is used for ranking.\n"
                "• You can revoke location consent at any time via <code>/revokelocation</code>.\n\n"
                "Do you consent to sharing your location for emergency proximity matching?"
            )
            kb = {
                "inline_keyboard": [
                    [{"text": "📍 I Consent & Share Location", "callback_data": "reg_loc:consent_yes"}],
                    [{"text": "❌ Decline & Cancel", "callback_data": "reg_loc:consent_no"}],
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=loc_consent_text, reply_markup=kb)

        elif step == "REG_LOCATION":
            if text in ("Skip Location", "⏭️ Skip Location", "/skip"):
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ <b>GPS Location Mandatory:</b>\n\n"
                        "GPS location sharing is mandatory for voluntary donor registration on RakthaSethu so nearby emergency patients can reach you.\n"
                        "District-only fallback registration is not permitted.\n\n"
                        "Please tap <b>📍 Share Current Location</b> below or type /cancel to abort."
                    ),
                )
                return

            if not message.location:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ <b>Native GPS Location Required:</b>\n"
                        "Typed place names or addresses cannot be used as GPS coordinates.\n"
                        "Please tap <b>📍 Share Current Location</b> below."
                    ),
                    reply_markup={
                        "keyboard": [
                            [{"text": "📍 Share Current Location", "request_location": True}],
                            [{"text": "❌ Cancel Registration"}]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True,
                    },
                )
                return

            lat = message.location.latitude
            lon = message.location.longitude

            if not math.isfinite(lat) or not math.isfinite(lon) or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                await self.client.send_message(
                    chat_id=chat_id,
                    text="⚠️ Received coordinates are out of valid range. Please share again or tap Skip Location:",
                )
                return

            await self.service.update_conversation(
                telegram_user_id=user_id,
                chat_id=chat_id,
                step="REG_CONFIRM",
                data_updates={"latitude": lat, "longitude": lon, "location_consent": True},
            )
            await self.client.send_message(
                chat_id=chat_id,
                text="✅ GPS coordinates received securely.",
                reply_markup={"remove_keyboard": True},
            )
            updated_conv = await self.service.get_conversation(user_id)
            await self.send_registration_summary(chat_id, user_id, updated_conv)

    def build_blood_group_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "A+", "callback_data": "bg:A+"}, {"text": "A-", "callback_data": "bg:A-"}],
                [{"text": "B+", "callback_data": "bg:B+"}, {"text": "B-", "callback_data": "bg:B-"}],
                [{"text": "AB+", "callback_data": "bg:AB+"}, {"text": "AB-", "callback_data": "bg:AB-"}],
                [{"text": "O+", "callback_data": "bg:O+"}, {"text": "O-", "callback_data": "bg:O-"}],
            ]
        }

    def build_units_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "1 Unit", "callback_data": "units:1"},
                    {"text": "2 Units", "callback_data": "units:2"},
                    {"text": "3 Units", "callback_data": "units:3"},
                ],
                [
                    {"text": "4 Units", "callback_data": "units:4"},
                    {"text": "5 Units", "callback_data": "units:5"},
                ],
            ]
        }

    def build_district_keyboard(self) -> Dict[str, Any]:
        rows = []
        for i in range(0, len(KERALA_DISTRICTS), 2):
            row = [{"text": KERALA_DISTRICTS[i], "callback_data": f"dist:{KERALA_DISTRICTS[i]}"}]
            if i + 1 < len(KERALA_DISTRICTS):
                row.append({"text": KERALA_DISTRICTS[i + 1], "callback_data": f"dist:{KERALA_DISTRICTS[i + 1]}"})
            rows.append(row)
        return {"inline_keyboard": rows}

    def build_date_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "Today", "callback_data": "date:0"},
                    {"text": "Tomorrow", "callback_data": "date:1"},
                    {"text": "In 2 Days", "callback_data": "date:2"},
                ]
            ]
        }

    def build_urgency_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "🟢 Normal", "callback_data": "urg:NORMAL"}],
                [{"text": "🟡 Urgent", "callback_data": "urg:URGENT"}],
                [{"text": "🔴 Critical / Emergency", "callback_data": "urg:CRITICAL"}],
            ]
        }
