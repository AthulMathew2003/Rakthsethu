from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import check_hospital_scope, get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import PaginatedData
from app.schemas.hospital import (
    HospitalCreate,
    HospitalListQuery,
    HospitalResponse,
    HospitalUpdate,
)
from app.services.hospital_service import HospitalService

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])


@router.post(
    "",
    response_model=ApiResponse[HospitalResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new hospital facility (SUPER_ADMIN only)",
)
async def create_hospital(
    data: HospitalCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    service = HospitalService(session)
    hospital = await service.create_hospital(data)
    return success_response(data=hospital, message="Hospital created successfully.")


@router.get(
    "",
    response_model=ApiResponse[PaginatedData[HospitalResponse]],
    summary="List and filter hospitals (Paginated)",
)
async def list_hospitals(
    search: Optional[str] = Query(None, description="Search term for name, code, district, address"),
    district: Optional[str] = Query(None, description="Filter by district"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = HospitalListQuery(
        search=search,
        district=district,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    service = HospitalService(session)
    paginated_result = await service.list_hospitals(query)
    return success_response(data=paginated_result, message="Hospitals retrieved successfully.")


@router.get(
    "/{id}",
    response_model=ApiResponse[HospitalResponse],
    summary="Get hospital details by ID",
)
async def get_hospital(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HospitalService(session)
    hospital = await service.get_hospital_by_id(id)
    return success_response(data=hospital, message="Hospital retrieved successfully.")


@router.patch(
    "/{id}",
    response_model=ApiResponse[HospitalResponse],
    summary="Update hospital details (SUPER_ADMIN or assigned HOSPITAL_ADMIN)",
)
async def update_hospital(
    id: int,
    data: HospitalUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    check_hospital_scope(current_user, id)
    service = HospitalService(session)
    hospital = await service.update_hospital(id, data)
    return success_response(data=hospital, message="Hospital updated successfully.")
