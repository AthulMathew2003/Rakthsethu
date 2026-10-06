from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import (
    ForbiddenException,
    HospitalAccessDeniedException,
    UnauthorizedException,
)
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

# HTTP Bearer token extractor
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that authenticates and extracts the active user from JWT Bearer token."""
    if not auth or not auth.credentials:
        raise UnauthorizedException("Authentication token is missing.")

    payload = decode_access_token(auth.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload: missing subject.")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid token payload: subject must be integer user ID.")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("User account associated with this token no longer exists.")

    if not user.is_active:
        raise UnauthorizedException("User account is deactivated.")

    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """RBAC dependency to restrict route access to specific user roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                f"Action forbidden. Requires one of roles: {[r.value for r in allowed_roles]}."
            )
        return current_user

    return role_checker


def check_hospital_scope(user: User, target_hospital_id: Optional[int]) -> None:
    """Helper to verify that hospital-scoped staff only access their own hospital's data."""
    if user.role == UserRole.SUPER_ADMIN:
        return

    if target_hospital_id is not None and user.hospital_id != target_hospital_id:
        raise HospitalAccessDeniedException(
            f"Access denied. User belongs to hospital {user.hospital_id}, cannot access hospital {target_hospital_id}."
        )
