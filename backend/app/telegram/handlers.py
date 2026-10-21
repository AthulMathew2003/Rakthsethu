from datetime import date, datetime, timedelta, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency, UserRole
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.blood_request import BloodRequestCreate
from app.services.blood_request_service import BloodRequestService
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
        elif text.startswith("/help"):
            await self.cmd_help(chat_id)
            return
        elif text.startswith("/cancel"):
            await self.cmd_cancel(chat_id, user_id)
            return
        elif text.startswith("/requestblood"):
            await self.start_request_blood(chat_id, user_id)
            return
        elif text.startswith("/status"):
            parts = text.split()
            req_code = parts[1] if len(parts) > 1 else None
            await self.cmd_status(chat_id, user_id, req_code)
            return
        elif text.startswith("/link"):
            parts = text.split()
            token = parts[1] if len(parts) > 1 else None
            username = message.from_user.username if message.from_user else None
            await self.cmd_link(chat_id, user_id, token, username)
            return

        # Check conversational state machine
        conv = await self.service.get_conversation(user_id)
        if conv and conv.current_step != "IDLE":
            await self.handle_conversation_step(conv, text, chat_id, user_id)
        else:
            # Unrecognized free text message
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "👋 Welcome to <b>RakthaSethu</b>. Please use the menu below or type /help for available options."
                ),
                reply_markup=self.build_main_menu_keyboard(),
            )

    # ─── Commands ─────────────────────────────────────────────────────────

    async def cmd_start(self, chat_id: int, user_id: int) -> None:
        await self.service.reset_conversation(user_id)
        welcome_text = (
            "🩸 <b>Welcome to RakthaSethu Blood Donation Network</b>\n\n"
            "RakthaSethu connects patients in clinical need with verified voluntary blood donors "
            "and hospital blood banks across Kerala.\n\n"
            "<b>Quick Actions:</b>\n"
            "• 🩸 <b>/requestblood</b> — Submit an urgent clinical blood request\n"
            "• 🔍 <b>/status [CODE]</b> — Check your blood request status\n"
            "• ℹ️ <b>/help</b> — Learn how to use this service\n"
            "• 🏥 <b>/link [TOKEN]</b> — Link hospital staff account"
        )
        await self.client.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=self.build_main_menu_keyboard(),
        )

    async def cmd_help(self, chat_id: int) -> None:
        help_text = (
            "ℹ️ <b>RakthaSethu Telegram Bot Guide</b>\n\n"
            "<b>Public Requester Commands:</b>\n"
            "• <code>/requestblood</code> — Guided, step-by-step submission for a blood request.\n"
            "• <code>/status &lt;REQ_CODE&gt;</code> — View the progress of a request you submitted (e.g. <code>/status REQ0001</code>).\n"
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
        await self.client.send_message(
            chat_id=chat_id,
            text="❌ Current conversation cancelled. No request was submitted.\nType /requestblood whenever you need to start again.",
            reply_markup=self.build_main_menu_keyboard(),
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

        if is_staff:
            status_text += "<i>[Authorized Staff View]</i>"
            kb = {
                "inline_keyboard": [
                    [{"text": "🔍 Check Matching Donors", "callback_data": f"staff_match:{req.id}"}]
                ]
            }
            await self.client.send_message(chat_id=chat_id, text=status_text, reply_markup=kb)
        else:
            status_text += (
                "<i>Donor outreach is actively coordinated with the hospital blood bank. "
                "Donor contact details are protected under RakthaSethu privacy rules.</i>"
            )
            await self.client.send_message(chat_id=chat_id, text=status_text)

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

        conv = await self.service.get_conversation(user_id)
        if not conv:
            return

        step = conv.current_step
        state_data = dict(conv.state_data or {})

        # 1. Main menu navigation
        if data_str == "menu:requestblood":
            await self.start_request_blood(chat_id, user_id)
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

        # 2. Staff Donor Matching Dispatch
        if data_str.startswith("staff_match:"):
            req_id_str = data_str.split(":")[1]
            try:
                req_id = int(req_id_str)
                await self.handle_staff_match_view(chat_id, user_id, req_id)
            except Exception as exc:
                logger.error("Error in staff_match: %s", exc)
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

        # 9. Confirmation Submit
        if step == "CONFIRMATION":
            if data_str == "req:cancel":
                await self.cmd_cancel(chat_id, user_id)
                return
            elif data_str == "req:confirm":
                await self.submit_blood_request(chat_id, user_id, state_data, cb.from_user.username)
                return

    async def submit_blood_request(
        self,
        chat_id: int,
        user_id: int,
        data: Dict[str, Any],
        username: Optional[str],
    ) -> None:
        try:
            # Construct validated domain schema
            req_dto = BloodRequestCreate(
                hospital_id=int(data["hospital_id"]),
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

            # Record private ownership binding in database
            await self.service.record_telegram_blood_request(
                blood_request_id=created_req.id,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                telegram_username=username,
            )

            # Reset conversation state
            await self.service.reset_conversation(user_id)

            success_msg = (
                "🎉 <b>Blood Request Submitted Successfully!</b>\n\n"
                f"📌 <b>Request Code:</b> <code>{created_req.request_code}</code>\n"
                f"🏥 <b>Assigned Hospital:</b> {created_req.hospital_name}\n"
                f"📊 <b>Status:</b> PENDING\n\n"
                f"Our network has logged this request with the hospital blood bank team.\n\n"
                f"Check your request status at any time with:\n"
                f"<code>/status {created_req.request_code}</code>"
            )
            await self.client.send_message(
                chat_id=chat_id,
                text=success_msg,
                reply_markup=self.build_main_menu_keyboard(),
            )
        except Exception as exc:
            logger.exception("Failed to submit blood request from Telegram: %s", exc)
            await self.client.send_message(
                chat_id=chat_id,
                text=f"⚠️ Failed to submit request: {exc}. Please type /cancel and try again.",
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

    def build_main_menu_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "🩸 Request Blood", "callback_data": "menu:requestblood"}],
                [{"text": "🔍 Check Request Status", "callback_data": "menu:status"}],
                [
                    {"text": "🏥 Staff Link", "callback_data": "menu:link"},
                    {"text": "ℹ️ Help", "callback_data": "menu:help"},
                ],
            ]
        }

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
