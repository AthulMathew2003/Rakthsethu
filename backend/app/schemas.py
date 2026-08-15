from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = "Admin"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# --- Donor Schemas ---
class DonorBase(BaseModel):
    name: str
    blood_group: str
    phone: str
    email: str
    location: str
    last_donation: Optional[str] = "Never"
    status: Optional[str] = "Active"
    total_donations: Optional[int] = 1
    age: Optional[int] = None
    gender: Optional[str] = None

class DonorCreate(DonorBase):
    pass

class DonorUpdate(BaseModel):
    name: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    last_donation: Optional[str] = None
    status: Optional[str] = None
    total_donations: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None

class DonorResponse(DonorBase):
    id: int
    donor_code: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedDonorsResponse(BaseModel):
    items: List[DonorResponse]
    total: int
    page: int
    limit: int
    pages: int
    locations: List[str]
    blood_groups: List[str]


# --- Blood Inventory Schemas ---
class InventoryItemBase(BaseModel):
    blood_group: str
    units_available: int
    units_reserved: Optional[int] = 0
    min_threshold: Optional[int] = 20
    status: Optional[str] = "Sufficient"

class InventoryItemUpdate(BaseModel):
    units_available: int
    units_reserved: Optional[int] = None
    min_threshold: Optional[int] = None

class InventoryItemResponse(InventoryItemBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Blood Request Schemas ---
class BloodRequestBase(BaseModel):
    patient_name: str
    blood_group: str
    units_requested: int = 1
    hospital_name: str
    location: str
    contact_phone: str
    urgency: Optional[str] = "Normal"  # Critical, Urgent, Normal
    status: Optional[str] = "Pending"  # Pending, In Progress, Completed, Cancelled
    time_ago: Optional[str] = None

class BloodRequestCreate(BloodRequestBase):
    pass

class BloodRequestStatusUpdate(BaseModel):
    status: str

class BloodRequestResponse(BloodRequestBase):
    id: int
    request_code: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Donation Schemas ---
class DonationBase(BaseModel):
    donor_name: str
    blood_group: str
    units: int = 1
    donation_date: str
    venue: str
    status: Optional[str] = "Completed"
    donor_id: Optional[int] = None

class DonationCreate(DonationBase):
    pass

class DonationResponse(DonationBase):
    id: int
    donation_code: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Camp Event Schemas ---
class CampEventBase(BaseModel):
    title: str
    location: str
    event_date: str
    time_slot: Optional[str] = "9:00 AM – 2:00 PM"
    organizer: str
    target_units: Optional[int] = 50
    collected_units: Optional[int] = 0
    status: Optional[str] = "Upcoming"

class CampEventCreate(CampEventBase):
    pass

class CampEventUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[str] = None
    time_slot: Optional[str] = None
    organizer: Optional[str] = None
    target_units: Optional[int] = None
    collected_units: Optional[int] = None
    status: Optional[str] = None

class CampEventResponse(CampEventBase):
    id: int
    camp_code: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Notification Schemas ---
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Dashboard Aggregated Stats Schemas ---
class StatCard(BaseModel):
    title: str
    value: str
    growth: Optional[str] = None
    status: Optional[str] = None
    colorClass: str
    iconType: str

class InventoryChartItem(BaseModel):
    group: str
    value: int

class RecentRequestItem(BaseModel):
    id: int
    group: str
    name: str
    location: str
    time: str
    status: str
    statusClass: str
    units: int
    hospital: str

class UpcomingCampSummary(BaseModel):
    id: Optional[int] = None
    title: str
    location: str
    event_date: str
    time_slot: str

class DashboardStatsResponse(BaseModel):
    stats: List[StatCard]
    donorStats: List[StatCard]
    inventoryData: List[InventoryChartItem]
    recentRequests: List[RecentRequestItem]
    upcomingCamp: Optional[UpcomingCampSummary] = None
    totalDonorsCount: int
    activeDonorsCount: int
    totalInventoryUnits: int
    totalRequestsCount: int
    totalUnitsDonated: int
