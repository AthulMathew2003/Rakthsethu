from datetime import date, datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blood_request import BloodRequest
from app.models.donor import Donor
from app.models.enums import BloodGroup, UserRole
from app.models.hospital import Hospital
from app.models.telegram import (
    TelegramBloodRequest,
    TelegramConversation,
    TelegramDonor,
    TelegramDonorReviewCase,
    TelegramLinkToken,
    TelegramLinkedStaff,
    TelegramUpdateAudit,
)
from app.models.user import User
from app.repositories.donor_repository import DonorRepository
from app.core.phone_utils import normalize_phone_number
from geoalchemy2.elements import WKTElement

logger = logging.getLogger("rakthasethu.telegram.service")


class TelegramService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── 1. Durable Idempotency & Replay Protection ───────────────────────

    async def start_update_processing(
        self,
        update_id: int,
        chat_id: Optional[int],
        user_id: Optional[int],
        update_type: str,
    ) -> Tuple[bool, str]:
        """
        Atomically inspect and lock update processing in PostgreSQL.
        Returns:
            (can_proceed, status_reason)
            can_proceed: True if the caller must process this update;
                         False if duplicate/already completed.
        """
        # Query existing audit record
        stmt = select(TelegramUpdateAudit).where(TelegramUpdateAudit.update_id == update_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            if existing.status == "COMPLETED":
                return False, "ALREADY_COMPLETED"
            elif existing.status == "PROCESSING":
                # Another worker or request is actively handling this update
                return False, "IN_PROGRESS"
            elif existing.status == "FAILED":
                # Retry: update state to processing
                existing.status = "PROCESSING"
                existing.error_message = None
                await self.session.commit()
                return True, "RETRYING"

        # Record new update
        audit = TelegramUpdateAudit(
            update_id=update_id,
            chat_id=chat_id,
            user_id=user_id,
            update_type=update_type,
            status="PROCESSING",
        )
        self.session.add(audit)
        try:
            await self.session.commit()
            return True, "NEW"
        except IntegrityError:
            await self.session.rollback()
            # Concurrent race condition: another process inserted update_id
            return False, "CONCURRENT_CONFLICT"

    async def mark_update_completed(self, update_id: int) -> None:
        stmt = select(TelegramUpdateAudit).where(TelegramUpdateAudit.update_id == update_id)
        result = await self.session.execute(stmt)
        audit = result.scalar_one_or_none()
        if audit:
            audit.status = "COMPLETED"
            audit.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def mark_update_failed(self, update_id: int, error_message: str) -> None:
        stmt = select(TelegramUpdateAudit).where(TelegramUpdateAudit.update_id == update_id)
        result = await self.session.execute(stmt)
        audit = result.scalar_one_or_none()
        if audit:
            audit.status = "FAILED"
            audit.error_message = error_message[:1000]
            await self.session.commit()

    # ─── 2. Persistent Conversation State Machine ─────────────────────────

    async def get_conversation(self, telegram_user_id: int) -> Optional[TelegramConversation]:
        stmt = select(TelegramConversation).where(TelegramConversation.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_conversation(
        self,
        telegram_user_id: int,
        chat_id: int,
        step: str,
        data_updates: Optional[Dict[str, Any]] = None,
    ) -> TelegramConversation:
        conv = await self.get_conversation(telegram_user_id)
        if conv is None:
            conv = TelegramConversation(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                current_step=step,
                state_data=data_updates or {},
            )
            self.session.add(conv)
        else:
            conv.chat_id = chat_id
            conv.current_step = step
            if data_updates:
                current_data = dict(conv.state_data or {})
                current_data.update(data_updates)
                conv.state_data = current_data
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get_or_create_conversation(
        self,
        telegram_user_id: int,
        chat_id: int,
        step: str = "IDLE",
        data: Optional[Dict[str, Any]] = None,
        data_updates: Optional[Dict[str, Any]] = None,
    ) -> TelegramConversation:
        """
        Gets an existing conversation or creates one, updating step and state data.
        Safe for repeated Telegram callback delivery and concurrent state transitions.
        Supports both `data` and `data_updates` keyword arguments.
        """
        effective_data = data if data is not None else data_updates
        return await self.update_conversation(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            step=step,
            data_updates=effective_data,
        )

    async def reset_conversation(self, telegram_user_id: int) -> None:
        conv = await self.get_conversation(telegram_user_id)
        if conv:
            conv.current_step = "IDLE"
            conv.state_data = {}
            await self.session.commit()

    async def lock_and_transition_confirmation(
        self, telegram_user_id: int
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Atomically inspects and locks conversation in CONFIRMATION step.
        If yes, transitions to SUBMITTING and returns (True, state_data).
        If already SUBMITTING or IDLE, returns (False, None) to prevent duplicate submissions.
        """
        stmt = (
            select(TelegramConversation)
            .where(TelegramConversation.telegram_user_id == telegram_user_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv or conv.current_step != "CONFIRMATION":
            return False, None

        state_data = dict(conv.state_data or {})
        conv.current_step = "SUBMITTING"
        await self.session.commit()
        return True, state_data

    # ─── 3. Request Ownership & Access Control ────────────────────────────

    async def record_telegram_blood_request(
        self,
        blood_request_id: int,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str] = None,
    ) -> TelegramBloodRequest:
        record = TelegramBloodRequest(
            blood_request_id=blood_request_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def verify_request_access(
        self,
        request_code: str,
        telegram_user_id: int,
    ) -> Tuple[bool, bool, Optional[BloodRequest], Optional[Hospital]]:
        """
        Verifies whether a Telegram user is authorized to inspect a blood request.
        Returns:
            (is_authorized, is_staff, blood_request, hospital)
        """
        # Fetch request with associated hospital
        stmt = (
            select(BloodRequest)
            .options(selectinload(BloodRequest.hospital))
            .where(func.upper(BloodRequest.request_code) == request_code.strip().upper())
        )
        result = await self.session.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            return False, False, None, None

        # Check 1: Is caller the verified public requester who submitted it?
        stmt_owner = select(TelegramBloodRequest).where(
            TelegramBloodRequest.blood_request_id == req.id,
            TelegramBloodRequest.telegram_user_id == telegram_user_id,
        )
        owner_res = await self.session.execute(stmt_owner)
        if owner_res.scalar_one_or_none() is not None:
            return True, False, req, req.hospital

        # Check 2: Is caller an authorized linked hospital staff member?
        linked_staff = await self.get_linked_staff(telegram_user_id)
        if linked_staff and linked_staff.is_active:
            user = linked_staff.user
            if user and user.is_active:
                if user.role == UserRole.SUPER_ADMIN or user.hospital_id == req.hospital_id:
                    return True, True, req, req.hospital

        return False, False, req, None

    async def verify_request_access_by_id(
        self,
        request_id: int,
        telegram_user_id: int,
    ) -> Tuple[bool, bool, Optional[BloodRequest], Optional[Hospital]]:
        """
        Verifies whether a Telegram user is authorized to inspect a blood request by database ID.
        Returns:
            (is_authorized, is_staff, blood_request, hospital)
        """
        stmt = (
            select(BloodRequest)
            .options(selectinload(BloodRequest.hospital))
            .where(BloodRequest.id == request_id)
        )
        result = await self.session.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            return False, False, None, None

        # Check 1: Is caller the verified public requester who submitted it?
        stmt_owner = select(TelegramBloodRequest).where(
            TelegramBloodRequest.blood_request_id == req.id,
            TelegramBloodRequest.telegram_user_id == telegram_user_id,
        )
        owner_res = await self.session.execute(stmt_owner)
        if owner_res.scalar_one_or_none() is not None:
            return True, False, req, req.hospital

        # Check 2: Is caller an authorized linked hospital staff member?
        linked_staff = await self.get_linked_staff(telegram_user_id)
        if linked_staff and linked_staff.is_active:
            user = linked_staff.user
            if user and user.is_active:
                if user.role == UserRole.SUPER_ADMIN or user.hospital_id == req.hospital_id:
                    return True, True, req, req.hospital

        return False, False, req, None

    # ─── 4. Secure Staff Account Linking ──────────────────────────────────

    async def create_link_token(self, user_id: int) -> str:
        """
        Generates a 10-minute cryptographically random token for linking
        an authenticated staff member to their Telegram account.
        """
        # Generate token in format: RST-XXXX-YYYY
        raw_part = secrets.token_hex(4).upper()
        plain_token = f"RST-{raw_part[:4]}-{raw_part[4:]}"
        token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

        link_token = TelegramLinkToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            is_used=False,
        )
        self.session.add(link_token)
        await self.session.commit()
        return plain_token

    async def redeem_link_token(
        self,
        plain_token: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[User]]:
        clean_token = plain_token.strip()
        token_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()

        stmt = (
            select(TelegramLinkToken)
            .options(selectinload(TelegramLinkToken.user))
            .where(TelegramLinkToken.token_hash == token_hash)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return False, "Invalid linking token. Please generate a fresh token from the portal.", None

        if record.is_used:
            return False, "This linking token has already been used.", None

        now = datetime.now(timezone.utc)
        if record.expires_at < now:
            return False, "Linking token has expired (10-minute validity exceeded). Please generate a new one.", None

        user = record.user
        if not user or not user.is_active:
            return False, "Associated application user account is inactive or not found.", None

        if user.role not in (UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF):
            return False, "Only authorized hospital staff or administrators can link a Telegram account.", None

        # Mark token as used
        record.is_used = True
        record.used_at = now

        # Insert or update linked staff record
        stmt_staff = select(TelegramLinkedStaff).where(
            TelegramLinkedStaff.telegram_user_id == telegram_user_id
        )
        staff_res = await self.session.execute(stmt_staff)
        staff = staff_res.scalar_one_or_none()

        if staff:
            staff.user_id = user.id
            staff.telegram_chat_id = telegram_chat_id
            staff.telegram_username = telegram_username
            staff.is_active = True
            staff.linked_at = now
        else:
            staff = TelegramLinkedStaff(
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                user_id=user.id,
                is_active=True,
                linked_at=now,
            )
            self.session.add(staff)

        await self.session.commit()
        return True, "Account successfully linked!", user

    async def get_linked_staff(self, telegram_user_id: int) -> Optional[TelegramLinkedStaff]:
        stmt = (
            select(TelegramLinkedStaff)
            .options(
                selectinload(TelegramLinkedStaff.user).selectinload(User.hospital)
            )
            .where(
                TelegramLinkedStaff.telegram_user_id == telegram_user_id,
                TelegramLinkedStaff.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ─── 5. Voluntary Donor Registration & State Transitions ─────────────

    async def lock_and_transition_registration(
        self, telegram_user_id: int
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Atomically inspects and locks conversation in REG_CONFIRM step.
        If confirmed, transitions to REG_SUBMITTING to prevent duplicate registrations.
        """
        stmt = (
            select(TelegramConversation)
            .where(TelegramConversation.telegram_user_id == telegram_user_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv or conv.current_step != "REG_CONFIRM":
            return False, None

        state_data = dict(conv.state_data or {})
        conv.current_step = "REG_SUBMITTING"
        await self.session.commit()
        return True, state_data

    async def get_donor_by_telegram_user_id(self, telegram_user_id: int) -> Optional[Donor]:
        """Finds active donor linked to a Telegram user ID."""
        try:
            stmt = (
                select(Donor)
                .join(TelegramDonor, Donor.id == TelegramDonor.donor_id)
                .where(TelegramDonor.telegram_user_id == telegram_user_id)
            )
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as exc:
            logger.debug("Could not query TelegramDonor table: %s", exc)
            return None

    async def record_telegram_donor(
        self,
        donor_id: int,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str] = None,
    ) -> Optional[TelegramDonor]:
        """Persists or updates TelegramDonor link."""
        try:
            stmt = select(TelegramDonor).where(TelegramDonor.telegram_user_id == telegram_user_id)
            res = await self.session.execute(stmt)
            link = res.scalar_one_or_none()
            if link:
                link.donor_id = donor_id
                link.telegram_chat_id = telegram_chat_id
                link.telegram_username = telegram_username
            else:
                link = TelegramDonor(
                    donor_id=donor_id,
                    telegram_user_id=telegram_user_id,
                    telegram_chat_id=telegram_chat_id,
                    telegram_username=telegram_username,
                )
                self.session.add(link)
            await self.session.commit()
            return link
        except Exception as exc:
            logger.warning("Could not persist TelegramDonor link: %s", exc)
            return None

    async def create_donor_review_case(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        phone: str,
        submitted_name: str,
        submitted_blood_group: str,
        submitted_district: str,
        existing_donor_id: Optional[int],
        reason: str,
    ) -> Optional[TelegramDonorReviewCase]:
        """Creates an admin review case for ambiguous duplicate registrations."""
        try:
            review_case = TelegramDonorReviewCase(
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                phone=phone,
                submitted_name=submitted_name,
                submitted_blood_group=submitted_blood_group,
                submitted_district=submitted_district,
                existing_donor_id=existing_donor_id,
                reason=reason,
                status="PENDING",
            )
            self.session.add(review_case)
            await self.session.commit()
            return review_case
        except Exception as exc:
            logger.warning("Could not persist TelegramDonorReviewCase: %s", exc)
            return None

    async def get_pending_donor_review_case(
        self, telegram_user_id: int
    ) -> Optional[TelegramDonorReviewCase]:
        """Finds any pending administrative review case for this Telegram user ID."""
        try:
            stmt = (
                select(TelegramDonorReviewCase)
                .where(
                    TelegramDonorReviewCase.telegram_user_id == telegram_user_id,
                    TelegramDonorReviewCase.status == "PENDING",
                )
                .order_by(TelegramDonorReviewCase.id.desc())
            )
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as exc:
            logger.debug("Could not query TelegramDonorReviewCase table: %s", exc)
            return None

    async def save_registered_donor(
        self,
        telegram_user_id: int,
        chat_id: int,
        username: Optional[str],
        data: Dict[str, Any],
    ) -> Tuple[str, Any]:
        """
        Safely saves or links a donor record.
        Returns:
            ("ALREADY_REGISTERED", existing_donor)
            ("CREATED", donor)
            ("UPDATED", existing_donor)
            ("REVIEW_CASE", review_case_or_data)
        """
        # Guard against duplicate registration if already linked
        already_linked = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if already_linked:
            return "ALREADY_REGISTERED", already_linked

        donor_repo = DonorRepository(self.session)
        raw_phone = data.get("phone", "")
        normalized_phone = normalize_phone_number(raw_phone)

        # Check existing donor by normalized phone
        existing = await donor_repo.get_by_phone(normalized_phone)

        if existing:
            # Check if association can be established reliably
            existing_name = (existing.full_name or "").strip().lower()
            submitted_name = (data.get("full_name") or "").strip().lower()
            existing_bg = existing.blood_group.value if hasattr(existing.blood_group, "value") else str(existing.blood_group)
            submitted_bg = str(data.get("blood_group", ""))

            name_matches = (existing_name == submitted_name)
            bg_matches = (existing_bg == submitted_bg)

            if name_matches and bg_matches:
                # Safe update and link (preserve existing availability)
                existing.district = str(data.get("district", existing.district)).strip()
                existing.is_active = True

                if data.get("location_consent") and data.get("latitude") is not None and data.get("longitude") is not None:
                    existing.location = WKTElement(
                        f"POINT({data['longitude']} {data['latitude']})", srid=4326
                    )
                    existing.location_consent = True
                    existing.location_consent_recorded_at = datetime.now(timezone.utc)

                await self.session.commit()
                await self.record_telegram_donor(existing.id, telegram_user_id, chat_id, username)
                return "UPDATED", existing
            else:
                # Conflicting record: create admin review case rather than overwriting
                reason = (
                    f"Phone matches existing donor {existing.donor_code} ({existing.full_name}, {existing_bg}), "
                    f"but submitted details conflict ({data.get('full_name')}, {submitted_bg})."
                )
                case = await self.create_donor_review_case(
                    telegram_user_id=telegram_user_id,
                    telegram_chat_id=chat_id,
                    phone=normalized_phone,
                    submitted_name=str(data.get("full_name", "")),
                    submitted_blood_group=submitted_bg,
                    submitted_district=str(data.get("district", "")),
                    existing_donor_id=existing.id,
                    reason=reason,
                )
                return "REVIEW_CASE", case or {"case_id": f"REV-{telegram_user_id}", "reason": reason}

        # Ordinary new registration - mandatory GPS location consent validation
        if not data.get("location_consent") or data.get("latitude") is None or data.get("longitude") is None:
            raise ValueError("GPS location sharing and explicit location consent are mandatory to complete voluntary donor registration.")

        donor_code = await donor_repo.generate_next_donor_code()

        location_geom = WKTElement(
            f"POINT({data['longitude']} {data['latitude']})", srid=4326
        )
        consent_val = True
        consent_time = datetime.now(timezone.utc)

        donor = Donor(
            donor_code=donor_code,
            hospital_id=None,
            full_name=str(data["full_name"]).strip(),
            blood_group=BloodGroup(data["blood_group"]),
            phone=normalized_phone,
            district=str(data["district"]).strip(),
            location=location_geom,
            location_consent=consent_val,
            location_consent_recorded_at=consent_time,
            is_active=True,
            is_available=True,
        )

        try:
            await donor_repo.add(donor)
            await self.session.commit()
            await self.record_telegram_donor(donor.id, telegram_user_id, chat_id, username)
            return "CREATED", donor
        except IntegrityError:
            await self.session.rollback()
            # Concurrent race condition: phone was just inserted
            existing_after_race = await donor_repo.get_by_phone(normalized_phone)
            if existing_after_race:
                return "UPDATED", existing_after_race
            raise

    async def revoke_donor_location(self, telegram_user_id: int) -> Tuple[bool, str, Optional[str]]:
        """
        Revokes location consent for the donor associated with this Telegram account.
        Disables location-based matching and clears coordinates.
        """
        donor = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if not donor:
            # Fallback check: lookup conversation for phone
            conv = await self.get_conversation(telegram_user_id)
            if conv and conv.state_data and "phone" in conv.state_data:
                norm_phone = normalize_phone_number(conv.state_data["phone"])
                donor_repo = DonorRepository(self.session)
                donor = await donor_repo.get_by_phone(norm_phone)

        if not donor:
            return False, "No active voluntary donor registration was found for this Telegram account.", None

        donor.location = None
        donor.location_consent = False
        donor.location_consent_recorded_at = None
        await self.session.commit()
        return True, "Your GPS location consent has been successfully revoked. You will now be matched based on your district only.", donor.donor_code

    async def toggle_donor_availability(
        self, telegram_user_id: int
    ) -> Tuple[bool, str, Optional[bool]]:
        """
        Safely toggles availability status (is_available) for the registered voluntary donor.
        """
        donor = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if not donor:
            return False, "No active voluntary donor registration was found for this Telegram account.", None

        new_status = not donor.is_available
        donor.is_available = new_status
        await self.session.commit()
        status_word = "Available for emergency matching" if new_status else "Temporarily Unavailable"
        return True, f"Your availability has been updated to: <b>{status_word}</b>.", new_status

    async def update_donor_district(
        self, telegram_user_id: int, new_district: str
    ) -> Tuple[bool, str]:
        """
        Safely updates the home district for the registered voluntary donor.
        """
        donor = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if not donor:
            return False, "No active voluntary donor registration was found for this Telegram account."

        donor.district = new_district.strip()
        await self.session.commit()
        return True, f"Your home district has been updated to <b>{donor.district}</b>."

    async def get_donor_last_donation_info(
        self, telegram_user_id: int
    ) -> Tuple[Optional[date], Optional[str], Optional[date], Optional[date]]:
        """
        Returns (effective_date, effective_source, verified_date, self_reported_date)
        for the voluntary donor linked to this Telegram user.
        """
        donor = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if not donor:
            return None, None, None, None

        donor_repo = DonorRepository(self.session)
        verified_date = await donor_repo.get_latest_donation_date(donor.id)
        self_date = donor.last_donation_date
        eff_date, source = await donor_repo.get_effective_last_donation_date(donor)
        return eff_date, source, verified_date, self_date

    async def update_donor_last_donation_date(
        self,
        telegram_user_id: int,
        new_date: Optional[date],
        source: Optional[str] = "SELF_REPORTED",
    ) -> Tuple[bool, str, Optional[Donor]]:
        """
        Transactionally updates the self-reported last blood donation date for the authenticated donor.
        - Resolves donor solely by telegram_user_id (no external ID spoofing).
        - Preserves existing hospital-verified donation ledger in donations table.
        - Tracks provenance: 'SELF_REPORTED' or 'NEVER_DONATED'.
        - Strictly leaves donor.is_available unchanged.
        """
        donor = await self.get_donor_by_telegram_user_id(telegram_user_id)
        if not donor:
            return False, "Unauthorized: No active voluntary donor registration is linked to this Telegram account.", None

        donor_repo = DonorRepository(self.session)
        verified_date = await donor_repo.get_latest_donation_date(donor.id)

        # 1. Clearing date / "Never Donated"
        if new_date is None:
            effective_source = source if source in ("NEVER_DONATED", "SELF_REPORTED") else None
            donor.last_donation_date = None
            donor.last_donation_date_source = effective_source
            donor.last_donation_date_updated_at = datetime.now(timezone.utc)
            # donor.is_available is deliberately untouched
            await self.session.commit()

            if verified_date:
                return (
                    True,
                    f"Self-reported status noted, but hospital-verified donation on {verified_date.strftime('%d-%m-%Y')} remains authoritative on record.",
                    donor,
                )
            if effective_source == "NEVER_DONATED":
                return True, "Your status has been recorded as: Confirmed Never Donated.", donor
            return True, "Your last donation date has been reset to: Donation history unknown / not recorded.", donor

        # 2. Date validation
        today = date.today()
        if new_date > today:
            return False, "Donation date cannot be in the future.", None
        if new_date < today - timedelta(days=365 * 50):
            return False, "Donation date cannot be more than 50 years in the past.", None

        # 3. Update self-reported fields on Donor (preserves verified ledger unchanged)
        donor.last_donation_date = new_date
        donor.last_donation_date_source = "SELF_REPORTED"
        donor.last_donation_date_updated_at = datetime.now(timezone.utc)
        # donor.is_available is deliberately untouched
        await self.session.commit()

        if verified_date and isinstance(verified_date, date) and verified_date > new_date:
            return (
                True,
                f"Date recorded as self-reported ({new_date.strftime('%d-%m-%Y')}). Note: Hospital-verified donation from {verified_date.strftime('%d-%m-%Y')} is more recent and will govern cooldown.",
                donor,
            )

        return True, f"Last donation date successfully updated to {new_date.strftime('%d-%m-%Y')} (Self-Reported).", donor


