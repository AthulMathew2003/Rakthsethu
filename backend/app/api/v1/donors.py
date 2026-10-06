from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import check_hospital_scope, get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import BloodGroup, UserRole
from app.models.user import User
from app.schemas.common import PaginatedData
from app.schemas.donor import (
    DonorCreate,
    DonorListQuery,
    DonorResponse,
    DonorUpdate,
)
from app.services.donor_service import DonorService

router = APIRouter(prefix="/donors", tags=["Donors"])


@router.post(
    "",
    response_model=ApiResponse[DonorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new blood donor",
)
async def create_donor(
    data: DonorCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    # Auto-assign hospital_id for hospital staff if omitted
    if current_user.role != UserRole.SUPER_ADMIN and data.hospital_id is None:
        data.hospital_id = current_user.hospital_id

    service = DonorService(session)
    donor = await service.create_donor(data)
    return success_response(data=donor, message="Donor registered successfully.")


@router.get(
    "",
    response_model=ApiResponse[PaginatedData[DonorResponse]],
    summary="List and filter blood donors (Paginated)",
)
async def list_donors(
    search: Optional[str] = Query(None, description="Search by name, code, phone, district, panchayat"),
    blood_group: Optional[BloodGroup] = Query(None, description="Filter by ABO/Rh blood group"),
    district: Optional[str] = Query(None, description="Filter by district"),
    is_available: Optional[bool] = Query(None, description="Filter by willingness availability"),
    hospital_id: Optional[int] = Query(None, description="Filter by sourcing hospital"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = DonorListQuery(
        search=search,
        blood_group=blood_group,
        district=district,
        is_available=is_available,
        hospital_id=hospital_id,
        page=page,
        page_size=page_size,
    )
    service = DonorService(session)
    paginated_result = await service.list_donors(query)
    return success_response(data=paginated_result, message="Donors retrieved successfully.")


@router.get(
    "/{id}",
    response_model=ApiResponse[DonorResponse],
    summary="Get donor details and latest donation date by ID",
)
async def get_donor(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DonorService(session)
    donor = await service.get_donor_by_id(id)
    return success_response(data=donor, message="Donor retrieved successfully.")


@router.patch(
    "/{id}",
    response_model=ApiResponse[DonorResponse],
    summary="Update donor profile or toggle availability/status",
)
async def update_donor(
    id: int,
    data: DonorUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = DonorService(session)
    donor = await service.update_donor(id, data)
    return success_response(data=donor, message="Donor updated successfully.")
