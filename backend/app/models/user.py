from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.donor_import_batch import DonorImportBatch


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    hospital_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", create_type=False),
        default=UserRole.STAFF,
        nullable=False,
    )
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    panchayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital", back_populates="users")
    uploaded_batches: Mapped[List["DonorImportBatch"]] = relationship("DonorImportBatch", back_populates="uploaded_by")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_hospital_id", "hospital_id"),
    )
