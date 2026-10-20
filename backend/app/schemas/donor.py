import math
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.models.enums import BloodGroup


class DonorLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees [-90, 90]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees [-180, 180]")
    consent_confirmed: bool = Field(
        ...,
        description="Explicit confirmation that donor consented to storing and using their GPS location for proximity blood matching",
    )

    @model_validator(mode="after")
    def validate_location_payload(self) -> "DonorLocationUpdate":
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("Latitude and longitude must be finite numeric values.")
        if not self.consent_confirmed:
            raise ValueError("Explicit donor consent is mandatory before storing or updating GPS location.")
        return self


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
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional GPS latitude [-90, 90]")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional GPS longitude [-180, 180]")
    location_consent: Optional[bool] = Field(None, description="Explicit donor consent for GPS tracking")

    @model_validator(mode="after")
    def validate_coordinates(self) -> "DonorCreate":
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None
        if has_lat ^ has_lon:
            raise ValueError("Both latitude and longitude must be provided together.")
        if has_lat and has_lon:
            if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
                raise ValueError("Latitude and longitude must be finite numeric values.")
            if self.location_consent is not True:
                raise ValueError("Explicit donor consent (location_consent=True) is mandatory when providing GPS coordinates.")
        return self


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
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="GPS latitude [-90, 90]")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="GPS longitude [-180, 180]")
    location_consent: Optional[bool] = Field(None, description="Explicit donor consent for GPS tracking")
    remove_location: Optional[bool] = Field(False, description="Set True to clear registered GPS location")

    @model_validator(mode="after")
    def validate_coordinates(self) -> "DonorUpdate":
        if self.remove_location:
            return self
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None
        if has_lat ^ has_lon:
            raise ValueError("Both latitude and longitude must be provided together.")
        if has_lat and has_lon:
            if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
                raise ValueError("Latitude and longitude must be finite numeric values.")
            if self.location_consent is not True:
                raise ValueError("Explicit donor consent (location_consent=True) is mandatory when updating GPS coordinates.")
        return self


class DonorResponse(DonorBase):
    id: int
    donor_code: str
    hospital_id: Optional[int] = None
    is_active: bool
    has_location: bool = Field(default=False, description="Whether donor has registered GPS coordinates")
    location_consent: bool = Field(default=False, description="Whether donor consented to location-based proximity matching")
    location_consent_recorded_at: Optional[datetime] = None
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
