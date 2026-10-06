from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Authenticate user and obtain JWT token",
)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    service = AuthService(session)
    token_resp = await service.authenticate_user(login_data)
    return success_response(data=token_resp, message="Authentication successful.")


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get current authenticated user profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AuthService(session)
    profile = await service.get_user_profile(current_user.id)
    return success_response(data=profile, message="User profile retrieved successfully.")


@router.post(
    "/users",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new administrative user account (SUPER_ADMIN only)",
)
async def create_user_account(
    user_data: UserCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    service = AuthService(session)
    new_user = await service.register_user(user_data)
    return success_response(data=new_user, message="User account created successfully.")
