from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import BloodGroup


class MatchDonorsRequest(BaseModel):
    blood_group: BloodGroup = Field(..., description="Recipient/Patient blood group")
    district: str = Field(..., min_length=1, max_length=100, description="Target district for matching")
    panchayat: Optional[str] = Field(None, max_length=100, description="Optional local body / taluk for proximity refinement")
    required_units: int = Field(1, ge=1, le=100, description="Number of units needed")
    required_date: Optional[date] = Field(None, description="Date blood is needed (defaults to current date)")
    donation_type: str = Field("Whole Blood", description="Donation type (Whole Blood, Platelets, Plasma)")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Maximum eligible donors to return")


class MatchedDonorItem(BaseModel):
    donor_id: int
    donor_code: str
    full_name: str
    blood_group: BloodGroup
    phone: str
    district: str
    panchayat: Optional[str] = None
    is_available: bool
    last_donation_date: Optional[date] = None
    eligible_from: Optional[date] = None
    days_since_last_donation: Optional[int] = None
    match_reason: str

    model_config = ConfigDict(from_attributes=True)


class MatchDonorsResponse(BaseModel):
    recipient_blood_group: BloodGroup
    compatible_blood_groups: List[BloodGroup]
    district: str
    panchayat: Optional[str] = None
    required_units: int
    required_date: date
    total_eligible_found: int
    items: List[MatchedDonorItem]
