from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency


class BloodRequestBase(BaseModel):
    hospital_id: int = Field(..., description="Requesting hospital ID")
    patient_name: str = Field(..., min_length=2, max_length=150, description="Patient name or clinical case ref")
    blood_group: BloodGroup
    units_requested: int = Field(default=1, gt=0, description="Units requested (must be > 0)")
    district: str = Field(..., min_length=2, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    contact_phone: str = Field(..., min_length=10, max_length=20)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    required_date: date = Field(..., description="Target fulfillment date")
    urgency: RequestUrgency = Field(default=RequestUrgency.NORMAL)
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    notes: Optional[str] = None


class BloodRequestCreate(BloodRequestBase):
    request_code: Optional[str] = Field(None, max_length=32, description="Optional custom code; auto-generated if omitted")


class BloodRequestUpdate(BaseModel):
    patient_name: Optional[str] = Field(None, min_length=2, max_length=150)
    blood_group: Optional[BloodGroup] = None
    units_requested: Optional[int] = Field(None, gt=0)
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    location: Optional[str] = None
    contact_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    required_date: Optional[date] = None
    urgency: Optional[RequestUrgency] = None
    status: Optional[RequestStatus] = None
    notes: Optional[str] = None


class BloodRequestResponse(BloodRequestBase):
    id: int
    request_code: str
    hospital_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BloodRequestListQuery(BaseModel):
    hospital_id: Optional[int] = None
    blood_group: Optional[BloodGroup] = None
    district: Optional[str] = None
    urgency: Optional[RequestUrgency] = None
    status: Optional[RequestStatus] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
