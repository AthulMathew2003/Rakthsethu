from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.enums import DonationStatus

if TYPE_CHECKING:
    from app.models.donor import Donor
    from app.models.hospital import Hospital


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    donation_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    donor_id: Mapped[int] = mapped_column(
        ForeignKey("donors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    hospital_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    donation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    donation_type: Mapped[str] = mapped_column(String(50), default="Voluntary", nullable=False)
    units_donated: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[DonationStatus] = mapped_column(
        SQLEnum(DonationStatus, name="donation_status_enum", create_type=False),
        default=DonationStatus.COMPLETED,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    donor: Mapped["Donor"] = relationship("Donor", back_populates="donations")
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital", back_populates="donations")

    __table_args__ = (
        CheckConstraint("units_donated > 0", name="chk_units_donated_positive"),
        Index("idx_donations_donor_id", "donor_id"),
        Index("idx_donations_hospital_id", "hospital_id"),
        Index("idx_donations_date_status", "donation_date", "status"),
    )
