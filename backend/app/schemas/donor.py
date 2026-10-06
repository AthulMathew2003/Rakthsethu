from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import BloodGroup


class DonorBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    blood_group: BloodGroup
    phone: str = Field(..., min_length=10, max_length=20, description="Contact phone number")
    gender: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    district: str = Field(..., min_length=2, max_length=100)
    panchayat: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    is_available: bool = Field(default=True, description="Opt-in willingness to donate")


class DonorCreate(DonorBase):
    donor_code: Optional[str] = Field(None, max_length=32, description="Optional custom code; auto-generated if omitted")
    hospital_id: Optional[int] = Field(None, description="Linked sourcing hospital if registered by hospital")


class DonorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    blood_group: Optional[BloodGroup] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    panchayat: Optional[str] = None
    address: Optional[str] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None
    hospital_id: Optional[int] = None


class DonorResponse(DonorBase):
    id: int
    donor_code: str
    hospital_id: Optional[int] = None
    is_active: bool
    last_donation_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DonorListQuery(BaseModel):
    search: Optional[str] = None
    blood_group: Optional[BloodGroup] = None
    district: Optional[str] = None
    is_available: Optional[bool] = None
    hospital_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
