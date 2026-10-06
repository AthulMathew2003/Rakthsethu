from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.donor import Donor
    from app.models.donation import Donation
    from app.models.blood_request import BloodRequest
    from app.models.donor_import_batch import DonorImportBatch


class Hospital(Base, TimestampMixin):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hospital_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hospital_type: Mapped[str] = mapped_column(String(50), default="Government", nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    panchayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    emergency_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="hospital")
    donors: Mapped[List["Donor"]] = relationship("Donor", back_populates="hospital")
    donations: Mapped[List["Donation"]] = relationship("Donation", back_populates="hospital")
    blood_requests: Mapped[List["BloodRequest"]] = relationship("BloodRequest", back_populates="hospital")
    import_batches: Mapped[List["DonorImportBatch"]] = relationship("DonorImportBatch", back_populates="hospital")

    __table_args__ = (
        Index("idx_hospitals_district", "district"),
        Index("idx_hospitals_is_active", "is_active"),
    )
