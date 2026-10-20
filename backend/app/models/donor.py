from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
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
    location: Mapped[Optional[Any]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
    )
    location_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location_consent_recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    @property
    def has_location(self) -> bool:
        return self.location is not None

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
        Index("idx_donors_location_gist", "location", postgresql_using="gist"),
    )
