from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class HospitalBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    hospital_type: str = Field(default="Government", max_length=50)
    district: str = Field(..., min_length=2, max_length=100)
    panchayat: Optional[str] = Field(None, max_length=100)
    address: str = Field(..., min_length=5)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    emergency_number: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HospitalCreate(HospitalBase):
    hospital_code: Optional[str] = Field(None, max_length=32, description="Optional custom code; auto-generated if omitted")


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    hospital_type: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    panchayat: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    emergency_number: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None


class HospitalResponse(HospitalBase):
    id: int
    hospital_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HospitalListQuery(BaseModel):
    search: Optional[str] = None
    district: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
