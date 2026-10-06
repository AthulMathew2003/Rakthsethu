from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import DonationStatus


class DonationBase(BaseModel):
    donor_id: int = Field(..., description="ID of the donor")
    hospital_id: Optional[int] = Field(None, description="ID of the collecting hospital")
    donation_date: date = Field(..., description="ISO Date (YYYY-MM-DD) of donation")
    donation_type: str = Field(default="Voluntary", max_length=50)
    units_donated: int = Field(default=1, gt=0, description="Whole units donated (must be > 0)")
    status: DonationStatus = Field(default=DonationStatus.COMPLETED)
    notes: Optional[str] = None


class DonationCreate(DonationBase):
    donation_code: Optional[str] = Field(None, max_length=32, description="Optional custom code; auto-generated if omitted")


class DonationUpdate(BaseModel):
    donation_date: Optional[date] = None
    donation_type: Optional[str] = None
    units_donated: Optional[int] = Field(None, gt=0)
    status: Optional[DonationStatus] = None
    hospital_id: Optional[int] = None
    notes: Optional[str] = None


class DonationResponse(DonationBase):
    id: int
    donation_code: str
    donor_name: Optional[str] = None
    donor_blood_group: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DonationListQuery(BaseModel):
    donor_id: Optional[int] = None
    hospital_id: Optional[int] = None
    status: Optional[DonationStatus] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
