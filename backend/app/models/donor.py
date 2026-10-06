from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import BloodGroup

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.donation import Donation


class Donor(Base, TimestampMixin):
    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    donor_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    hospital_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    blood_group: Mapped[BloodGroup] = mapped_column(
        SQLEnum(
            BloodGroup,
            name="blood_group_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    panchayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital", back_populates="donors")
    donations: Mapped[List["Donation"]] = relationship(
        "Donation",
        back_populates="donor",
        order_by="desc(Donation.donation_date)",
    )

    __table_args__ = (
        Index("idx_donors_blood_group", "blood_group"),
        Index("idx_donors_district", "district"),
        Index("idx_donors_active_available", "is_active", "is_available"),
        Index("idx_donors_matching_composite", "blood_group", "district", "is_active", "is_available"),
    )
