from datetime import date
import math
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.config import settings
from app.models.enums import BloodGroup


class MatchDonorsRequest(BaseModel):
    blood_group: BloodGroup = Field(..., description="Recipient/Patient blood group")
    district: Optional[str] = Field(None, min_length=1, max_length=100, description="Target district for matching")
    panchayat: Optional[str] = Field(None, max_length=100, description="Optional local body / taluk for proximity refinement")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Origin latitude [-90, 90]")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Origin longitude [-180, 180]")
    hospital_id: Optional[int] = Field(None, description="Optional hospital ID to derive spatial origin")
    radius_km: Optional[float] = Field(None, description="Search radius in kilometers")
    include_fallback: bool = Field(True, description="Whether to include coordinate-less donors via district fallback")
    required_units: int = Field(1, ge=1, le=100, description="Number of units needed")
    required_date: Optional[date] = Field(None, description="Date blood is needed (defaults to current date)")
    donation_type: str = Field("Whole Blood", description="Donation type (Whole Blood, Platelets, Plasma)")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Maximum eligible donors to return")

    @model_validator(mode="after")
    def validate_origin_spec(self) -> "MatchDonorsRequest":
        # 1. Finite checks and coordinate boundary checks
        if self.latitude is not None:
            if not math.isfinite(self.latitude) or self.latitude < -90.0 or self.latitude > 90.0:
                raise ValueError("Latitude must be a finite numeric value between -90 and 90 degrees.")
        if self.longitude is not None:
            if not math.isfinite(self.longitude) or self.longitude < -180.0 or self.longitude > 180.0:
                raise ValueError("Longitude must be a finite numeric value between -180 and 180 degrees.")

        # 2. Coordinate pairing check
        has_coords = self.latitude is not None and self.longitude is not None
        partial_coords = (self.latitude is not None) ^ (self.longitude is not None)
        if partial_coords:
            raise ValueError("Both latitude and longitude must be provided together.")

        # 3. Radius validation: strictly positive, finite, and <= MAX_PROXIMITY_RADIUS_KM
        if self.radius_km is not None:
            if not math.isfinite(self.radius_km):
                raise ValueError("radius_km must be a finite numeric value.")
            if self.radius_km <= 0:
                raise ValueError("Search radius must be greater than 0 km. Radius zero or negative is not supported.")
            if self.radius_km > settings.MAX_PROXIMITY_RADIUS_KM:
                raise ValueError(
                    f"Search radius ({self.radius_km} km) exceeds maximum allowed limit of {settings.MAX_PROXIMITY_RADIUS_KM} km."
                )

        # 4. At least one location criterion
        if not self.district and not has_coords and not self.hospital_id:
            raise ValueError("At least one location criteria (district, coordinates, or hospital_id) must be provided.")
        return self


class MatchedDonorItem(BaseModel):
    donor_id: int
    donor_code: str
    full_name: str
    blood_group: BloodGroup
    phone: str
    district: str
    panchayat: Optional[str] = None
    is_available: bool
    distance_km: Optional[float] = Field(
        None,
        description="Distance from origin in kilometres rounded to 1 decimal place; null for coordinate-less fallback candidates",
    )
    match_category: str = Field(
        "PROXIMITY",
        description="Match category: 'PROXIMITY', 'FALLBACK_DISTRICT', or 'DISTRICT_DEFAULT'",
    )
    last_donation_date: Optional[date] = None
    eligible_from: Optional[date] = None
    days_since_last_donation: Optional[int] = None
    match_reason: str

    model_config = ConfigDict(from_attributes=True)


class MatchDonorsResponse(BaseModel):
    recipient_blood_group: BloodGroup
    compatible_blood_groups: List[BloodGroup]
    district: Optional[str] = None
    panchayat: Optional[str] = None
    origin_type: str = Field(
        "DISTRICT_DEFAULT",
        description="Origin used: 'EXPLICIT_GPS', 'HOSPITAL_LOCATION', or 'DISTRICT_DEFAULT'",
    )
    origin_latitude: Optional[float] = Field(None, description="Origin latitude used for proximity calculation")
    origin_longitude: Optional[float] = Field(None, description="Origin longitude used for proximity calculation")
    radius_km: Optional[float] = Field(None, description="Search radius in kilometers used")
    required_units: int
    required_date: date
    total_eligible_found: int
    items: List[MatchedDonorItem]
