from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime

# ==========================================
# --- User Schemas ---
# ==========================================
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = "Citizen"
    district: Optional[str] = "Kottayam"
    panchayat: Optional[str] = None
    registered_date: Optional[str] = None
    last_active: Optional[str] = None
    status: Optional[str] = "Active"

class UserCreate(UserBase):
    password: Optional[str] = "password123"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    user_code: Optional[str] = None
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
    district: Optional[str] = None
    panchayat: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

class UserStatusUpdate(BaseModel):
    status: str


# ==========================================
# --- Donor Schemas ---
# ==========================================
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


# ==========================================
# --- Blood Inventory Summary & Batch Schemas ---
# ==========================================
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

class InventoryBatchBase(BaseModel):
    blood_group: str
    component: Optional[str] = "Whole Blood"
    available_units: int = 1
    reserved_units: Optional[int] = 0
    collection_date: str
    expiry_date: str
    storage_location: str
    status: Optional[str] = "Available"
    notes: Optional[str] = None

class InventoryBatchCreate(InventoryBatchBase):
    pass

class InventoryBatchUpdate(BaseModel):
    blood_group: Optional[str] = None
    component: Optional[str] = None
    available_units: Optional[int] = None
    reserved_units: Optional[int] = None
    collection_date: Optional[str] = None
    expiry_date: Optional[str] = None
    storage_location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class InventoryBatchAdjust(BaseModel):
    type: str  # "add" or "remove"
    quantity: int
    reason: Optional[str] = None

class InventoryBatchResponse(InventoryBatchBase):
    id: int
    batch_code: str
    total_units: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- Blood Request Schemas ---
# ==========================================
class BloodRequestBase(BaseModel):
    patient_name: str
    blood_group: str
    units_requested: int = 1
    hospital_name: str
    district: Optional[str] = "Kottayam"
    location: Optional[str] = "Kottayam"
    contact_phone: str
    emergency_contact: Optional[str] = None
    required_date: Optional[str] = None
    urgency: Optional[str] = "Normal"  # Critical, Urgent, Normal
    status: Optional[str] = "Pending"  # Pending, Approved, In Progress, Fulfilled, Rejected, Cancelled
    notes: Optional[str] = None
    time_ago: Optional[str] = None

class BloodRequestCreate(BloodRequestBase):
    pass

class BloodRequestUpdate(BaseModel):
    patient_name: Optional[str] = None
    blood_group: Optional[str] = None
    units_requested: Optional[int] = None
    hospital_name: Optional[str] = None
    district: Optional[str] = None
    location: Optional[str] = None
    contact_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    required_date: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class BloodRequestStatusUpdate(BaseModel):
    status: str

class BloodRequestResponse(BloodRequestBase):
    id: int
    request_code: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- Donation Schemas ---
# ==========================================
class DonationBase(BaseModel):
    donor_name: str
    blood_group: str
    phone: Optional[str] = None
    email: Optional[str] = None
    district: Optional[str] = "Kottayam"
    address: Optional[str] = None
    donation_date: str
    donation_type: Optional[str] = "Voluntary"
    units: int = 1
    hospital: Optional[str] = None
    venue: Optional[str] = "Blood Bank"
    status: Optional[str] = "Completed"
    notes: Optional[str] = None
    donor_id: Optional[int] = None

class DonationCreate(DonationBase):
    pass

class DonationUpdate(BaseModel):
    donor_name: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    donation_date: Optional[str] = None
    donation_type: Optional[str] = None
    units: Optional[int] = None
    hospital: Optional[str] = None
    venue: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class DonationStatusUpdate(BaseModel):
    status: str

class DonationResponse(DonationBase):
    id: int
    donation_code: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- Camp & Campus Event Schemas ---
# ==========================================
class CampEventBase(BaseModel):
    title: str
    type: Optional[str] = "Blood Donation"
    location: str
    venue: Optional[str] = None
    event_date: str
    start_time: Optional[str] = "09:00 AM"
    end_time: Optional[str] = "03:00 PM"
    time_slot: Optional[str] = "9:00 AM – 2:00 PM"
    organizer: str
    participants: Optional[int] = 0
    max_participants: Optional[int] = 100
    target_units: Optional[int] = 50
    collected_units: Optional[int] = 0
    description: Optional[str] = None
    contact_number: Optional[str] = None
    registration_required: Optional[bool] = False
    registration_deadline: Optional[str] = None
    image_banner: Optional[str] = None
    status: Optional[str] = "Upcoming"

class CampEventCreate(CampEventBase):
    pass

class CampEventUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    time_slot: Optional[str] = None
    organizer: Optional[str] = None
    participants: Optional[int] = None
    max_participants: Optional[int] = None
    target_units: Optional[int] = None
    collected_units: Optional[int] = None
    description: Optional[str] = None
    contact_number: Optional[str] = None
    registration_required: Optional[bool] = None
    registration_deadline: Optional[str] = None
    image_banner: Optional[str] = None
    status: Optional[str] = None

class CampEventStatusUpdate(BaseModel):
    status: str

class CampEventResponse(CampEventBase):
    id: int
    camp_code: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- Hospital Schemas ---
# ==========================================
class HospitalBase(BaseModel):
    name: str
    type: Optional[str] = "Government"  # Government, Private
    district: Optional[str] = "Kottayam"
    panchayat: Optional[str] = None
    address: str
    phone: str
    email: Optional[str] = None
    emergency_number: Optional[str] = "108"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    services: Optional[str] = None  # JSON string or comma-separated list
    status: Optional[str] = "Active"

class HospitalCreate(HospitalBase):
    pass

class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    district: Optional[str] = None
    panchayat: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_number: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    services: Optional[str] = None
    status: Optional[str] = None

class HospitalResponse(HospitalBase):
    id: int
    hospital_code: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- System Settings Schemas ---
# ==========================================
class SettingsSaveRequest(BaseModel):
    general: Optional[Dict[str, Any]] = None
    profile: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    appearance: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    system: Optional[Dict[str, Any]] = None

class ProfileUpdateRequest(BaseModel):
    fullName: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    district: Optional[str] = None
    panchayat: Optional[str] = None
    avatar: Optional[str] = None


# ==========================================
# --- Activity Log & Notification Schemas ---
# ==========================================
class ActivityLogResponse(BaseModel):
    id: int
    category: str
    activity: str
    count: int
    status: str
    log_date: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==========================================
# --- Dashboard Aggregated Stats Schemas ---
# ==========================================
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
    hospitalsCount: Optional[int] = 0
    eventsCount: Optional[int] = 0
    usersCount: Optional[int] = 0
