from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
from typing import Optional
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="Admin")  # Admin, Staff, Donor
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
    __tablename__ = "blood_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    blood_group: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    units_available: Mapped[int] = mapped_column(Integer, default=0)
    units_reserved: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String, default="Sufficient")  # Sufficient, Low, Critical
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # REQ001
    patient_name: Mapped[str] = mapped_column(String, nullable=False)
    blood_group: Mapped[str] = mapped_column(String, nullable=False, index=True)
    units_requested: Mapped[int] = mapped_column(Integer, default=1)
    hospital_name: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    contact_phone: Mapped[str] = mapped_column(String, nullable=False)
    urgency: Mapped[str] = mapped_column(String, default="Normal")  # Critical, Urgent, Normal
    status: Mapped[str] = mapped_column(String, default="Pending", index=True)  # Pending, In Progress, Completed, Cancelled
    time_ago: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donation_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    donor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("donors.id", ondelete="SET NULL"), nullable=True)
    donor_name: Mapped[str] = mapped_column(String, nullable=False)
    blood_group: Mapped[str] = mapped_column(String, nullable=False)
    units: Mapped[int] = mapped_column(Integer, default=1)
    donation_date: Mapped[str] = mapped_column(String, nullable=False)
    venue: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="Completed")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CampEvent(Base):
    __tablename__ = "camps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camp_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    event_date: Mapped[str] = mapped_column(String, nullable=False)
    time_slot: Mapped[str] = mapped_column(String, default="9:00 AM – 2:00 PM")
    organizer: Mapped[str] = mapped_column(String, nullable=False)
    target_units: Mapped[int] = mapped_column(Integer, default=50)
    collected_units: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="Upcoming")  # Upcoming, Ongoing, Completed, Cancelled
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="info")  # urgent, alert, info, success
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
