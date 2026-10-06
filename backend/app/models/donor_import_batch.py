from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.enums import ImportStatus

if TYPE_CHECKING:
    from app.models.hospital import Hospital
    from app.models.user import User


class DonorImportBatch(Base):
    __tablename__ = "donor_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    hospital_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), default="csv", nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        SQLEnum(
            ImportStatus,
            name="import_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ImportStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = relationship("Hospital", back_populates="import_batches")
    uploaded_by: Mapped[Optional["User"]] = relationship("User", back_populates="uploaded_batches")

    __table_args__ = (
        Index("idx_import_batches_hospital_id", "hospital_id"),
        Index("idx_import_batches_status", "status"),
    )
