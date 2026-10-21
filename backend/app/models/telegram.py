from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.blood_request import BloodRequest
    from app.models.user import User


class TelegramUpdateAudit(Base):
    """
    Durable update tracking for Telegram webhook idempotency.
    Guarantees exactly-once processing across server restarts and concurrent deliveries.
    """
    __tablename__ = "telegram_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    update_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    update_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PROCESSING", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramBloodRequest(Base):
    """
    Records request ownership for Telegram-originated blood requests separately from notes.
    Preserves privacy: Telegram user IDs are never exposed in public REST schemas.
    """
    __tablename__ = "telegram_blood_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    blood_request_id: Mapped[int] = mapped_column(
        ForeignKey("blood_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    blood_request: Mapped["BloodRequest"] = relationship("BloodRequest", backref="telegram_origin")

    __table_args__ = (
        Index("idx_telegram_user_blood_request", "telegram_user_id", "blood_request_id"),
    )


class TelegramLinkToken(Base):
    """
    Short-lived, single-use, cryptographically hashed tokens for linking
    web application staff users to Telegram accounts.
    """
    __tablename__ = "telegram_link_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class TelegramLinkedStaff(Base):
    """
    Persistent mapping of authenticated hospital staff users to Telegram user IDs.
    Permissions are re-validated on every privileged command against the live User record.
    """
    __tablename__ = "telegram_linked_staff"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class TelegramConversation(Base):
    """
    Persistent conversational state machine for multi-step bot dialogs (e.g. /requestblood).
    Survives serverless restarts and idle sleep cycles without state loss.
    """
    __tablename__ = "telegram_conversations"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_step: Mapped[str] = mapped_column(String(32), default="IDLE", nullable=False)
    state_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TelegramDonor(Base):
    """
    Persistent mapping of voluntary donors to their Telegram accounts.
    Allows donors to manage their registration, update availability, or revoke location consent.
    """
    __tablename__ = "telegram_donors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(
        ForeignKey("donors.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TelegramDonorReviewCase(Base):
    """
    Records ambiguous duplicate registrations (e.g. same phone number but conflicting name/blood group)
    for hospital/system administrator review without overwriting or merging donor records.
    """
    __tablename__ = "telegram_donor_review_cases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    submitted_name: Mapped[str] = mapped_column(String(150), nullable=False)
    submitted_blood_group: Mapped[str] = mapped_column(String(10), nullable=False)
    submitted_district: Mapped[str] = mapped_column(String(100), nullable=False)
    existing_donor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("donors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

