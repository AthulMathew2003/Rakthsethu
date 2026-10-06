from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    DuplicateResourceException,
    InvalidCredentialsException,
    ResourceNotFoundException,
    UnauthorizedException,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.hospital_repository import HospitalRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.hospital_repo = HospitalRepository(session)

    async def authenticate_user(self, login_data: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise InvalidCredentialsException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException("Account is disabled. Please contact an administrator.")

        if not verify_password(login_data.password, user.hashed_password):
            raise InvalidCredentialsException("Invalid email or password.")

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()

        # Generate JWT access token
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            hospital_id=user.hospital_id,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=60 * 60,
            user=UserResponse.model_validate(user),
        )

    async def get_user_profile(self, user_id: int) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        return UserResponse.model_validate(user)

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise DuplicateResourceException("User", "email", user_data.email)

        if user_data.hospital_id:
            hospital = await self.hospital_repo.get_by_id(user_data.hospital_id)
            if not hospital:
                raise ResourceNotFoundException("Hospital", user_data.hospital_id)

        user_code = await self.user_repo.generate_next_user_code()
        hashed_pwd = hash_password(user_data.password)

        new_user = User(
            user_code=user_code,
            hospital_id=user_data.hospital_id,
            email=user_data.email.lower().strip(),
            hashed_password=hashed_pwd,
            full_name=user_data.full_name.strip(),
            phone_number=user_data.phone_number,
            role=user_data.role,
            district=user_data.district,
            panchayat=user_data.panchayat,
            is_active=True,
        )

        await self.user_repo.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        return UserResponse.model_validate(new_user)
