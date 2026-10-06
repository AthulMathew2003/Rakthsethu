from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency

if TYPE_CHECKING:
    from app.models.hospital import Hospital


class BloodRequest(Base, TimestampMixin):
    __tablename__ = "blood_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    hospital_id: Mapped[int] = mapped_column(
        ForeignKey("hospitals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_name: Mapped[str] = mapped_column(String(150), nullable=False)
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
    units_requested: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    required_date: Mapped[date] = mapped_column(Date, nullable=False)
    urgency: Mapped[RequestUrgency] = mapped_column(
        SQLEnum(RequestUrgency, name="request_urgency_enum", create_type=False),
        default=RequestUrgency.NORMAL,
        nullable=False,
        index=True,
    )
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status_enum", create_type=False),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="blood_requests")

    __table_args__ = (
        CheckConstraint("units_requested > 0", name="chk_units_requested_positive"),
        Index("idx_requests_status", "status"),
        Index("idx_requests_urgency", "urgency"),
        Index("idx_requests_district", "district"),
        Index("idx_requests_blood_group", "blood_group"),
        Index("idx_requests_hospital_id", "hospital_id"),
    )
