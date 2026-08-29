from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
from typing import Optional, List
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_code: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="Citizen")  # Citizen, Panchayat Admin, Department Admin, Staff, Super Admin, Admin
    district: Mapped[Optional[str]] = mapped_column(String, default="Kottayam")
    panchayat: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    registered_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_active: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Active")  # Active, Inactive, Suspended
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class Donor(Base):
    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # e.g. DON001
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    blood_group: Mapped[str] = mapped_column(String, nullable=False, index=True)  # O+, A+, B+, AB+, etc.
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False, index=True)
    last_donation: Mapped[str] = mapped_column(String, default="Never")
    status: Mapped[str] = mapped_column(String, default="Active", index=True)  # Active, Inactive
    total_donations: Mapped[int] = mapped_column(Integer, default=1)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class BloodInventory(Base):
    """Aggregated blood group level inventory summary (for dashboard overview)"""
    __tablename__ = "blood_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    blood_group: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    units_available: Mapped[int] = mapped_column(Integer, default=0)
    units_reserved: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String, default="Sufficient")  # Sufficient, Low, Critical
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BloodInventoryBatch(Base):
    """Detailed blood stock batches with components, expiry dates, locations"""
    __tablename__ = "blood_inventory_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # e.g. INV001
    blood_group: Mapped[str] = mapped_column(String, nullable=False, index=True)
    component: Mapped[str] = mapped_column(String, default="Whole Blood", index=True)  # Whole Blood, Packed RBC, Plasma, Platelets, Cryoprecipitate
    available_units: Mapped[int] = mapped_column(Integer, default=1)
    reserved_units: Mapped[int] = mapped_column(Integer, default=0)
    collection_date: Mapped[str] = mapped_column(String, nullable=False)
    expiry_date: Mapped[str] = mapped_column(String, nullable=False)
    storage_location: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="Available")  # Available, Low Stock, Critical, Reserved, Expired
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # BR001, REQ001
    patient_name: Mapped[str] = mapped_column(String, nullable=False)
    blood_group: Mapped[str] = mapped_column(String, nullable=False, index=True)
    units_requested: Mapped[int] = mapped_column(Integer, default=1)
    hospital_name: Mapped[str] = mapped_column(String, nullable=False)
    district: Mapped[str] = mapped_column(String, default="Kottayam", index=True)
    location: Mapped[str] = mapped_column(String, default="Kottayam")
    contact_phone: Mapped[str] = mapped_column(String, nullable=False)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    required_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    urgency: Mapped[str] = mapped_column(String, default="Normal")  # Critical, Urgent, Normal
    status: Mapped[str] = mapped_column(String, default="Pending", index=True)  # Pending, Approved, In Progress, Fulfilled, Rejected, Cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_ago: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donation_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    donor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("donors.id", ondelete="SET NULL"), nullable=True)
    donor_name: Mapped[str] = mapped_column(String, nullable=False)
    blood_group: Mapped[str] = mapped_column(String, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String, default="Kottayam")
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    donation_date: Mapped[str] = mapped_column(String, nullable=False)
    donation_type: Mapped[str] = mapped_column(String, default="Voluntary")  # Voluntary, Replacement, Camp Donation, Directed Donation
    units: Mapped[int] = mapped_column(Integer, default=1)
    hospital: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    venue: Mapped[str] = mapped_column(String, default="Blood Bank")
    status: Mapped[str] = mapped_column(String, default="Completed")  # Completed, Scheduled, In Progress, Cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampEvent(Base):
    __tablename__ = "camps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camp_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="Blood Donation")  # Blood Donation, Health Camp, Awareness Program, Volunteer Activity, etc.
    location: Mapped[str] = mapped_column(String, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_date: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[Optional[str]] = mapped_column(String, default="09:00 AM")
    end_time: Mapped[Optional[str]] = mapped_column(String, default="03:00 PM")
    time_slot: Mapped[str] = mapped_column(String, default="9:00 AM – 2:00 PM")
    organizer: Mapped[str] = mapped_column(String, nullable=False)
    participants: Mapped[int] = mapped_column(Integer, default=0)
    max_participants: Mapped[int] = mapped_column(Integer, default=100)
    target_units: Mapped[int] = mapped_column(Integer, default=50)
    collected_units: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    registration_required: Mapped[bool] = mapped_column(Boolean, default=False)
    registration_deadline: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_banner: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Upcoming")  # Draft, Upcoming, Ongoing, Completed, Cancelled
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hospital_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # HOSP001
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, default="Government")  # Government, Private
    district: Mapped[str] = mapped_column(String, default="Kottayam", index=True)
    panchayat: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emergency_number: Mapped[str] = mapped_column(String, default="108")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    services: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or comma-separated services
    status: Mapped[str] = mapped_column(String, default="Active")  # Active, Inactive
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # general, profile, notifications, appearance, security, system
    settings_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Blood Requests, Blood Donations, Blood Inventory, Users, Campus Events, Hospitals
    activity: Mapped[str] = mapped_column(String, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="Completed")
    log_date: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM-DD
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="info")  # urgent, alert, info, success
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
