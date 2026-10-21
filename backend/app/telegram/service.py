from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blood_request import BloodRequest
from app.models.enums import UserRole
from app.models.hospital import Hospital
from app.models.telegram import (
    TelegramBloodRequest,
    TelegramConversation,
    TelegramLinkToken,
    TelegramLinkedStaff,
    TelegramUpdateAudit,
)
from app.models.user import User

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
