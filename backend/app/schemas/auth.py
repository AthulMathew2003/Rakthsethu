from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User login email")
    password: str = Field(..., min_length=6, description="User login password")


class UserResponse(BaseModel):
    id: int
    user_code: str
    hospital_id: Optional[int] = None
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    role: UserRole
    district: Optional[str] = None
    panchayat: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone_number: Optional[str] = None
    role: UserRole = UserRole.STAFF
    hospital_id: Optional[int] = None
    district: Optional[str] = None
    panchayat: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone_number: Optional[str] = None
    district: Optional[str] = None
    panchayat: Optional[str] = None
    is_active: Optional[bool] = None
    hospital_id: Optional[int] = None
    role: Optional[UserRole] = None
