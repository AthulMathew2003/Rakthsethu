from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import check_hospital_scope, get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import BloodGroup, UserRole
from app.models.user import User
from app.schemas.common import PaginatedData
from app.core.exceptions import HospitalAccessDeniedException
from app.schemas.donor import (
    DonorCreate,
    DonorListQuery,
    DonorLocationUpdate,
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
    elif current_user.role != UserRole.SUPER_ADMIN and data.hospital_id != current_user.hospital_id:
        raise HospitalAccessDeniedException("Hospital staff cannot register donors for another hospital.")

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
    if current_user.role != UserRole.SUPER_ADMIN:
        existing = await service.get_donor_by_id(id)
        if existing.hospital_id is None or existing.hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException(
                f"Access denied. User belongs to hospital {current_user.hospital_id}, cannot manage donor with hospital {existing.hospital_id}."
            )
        if data.hospital_id is not None and data.hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException("Hospital staff cannot transfer donors to another hospital.")

    donor = await service.update_donor(id, data)
    return success_response(data=donor, message="Donor updated successfully.")


@router.put(
    "/{id}/location",
    response_model=ApiResponse[DonorResponse],
    summary="Set or update donor GPS coordinates",
)
async def update_donor_location(
    id: int,
    data: DonorLocationUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = DonorService(session)
    if current_user.role != UserRole.SUPER_ADMIN:
        existing = await service.get_donor_by_id(id)
        if existing.hospital_id is None or existing.hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException(
                f"Access denied. User belongs to hospital {current_user.hospital_id}, cannot manage donor with hospital {existing.hospital_id}."
            )

    donor = await service.update_donor_location(id, data.latitude, data.longitude)
    return success_response(data=donor, message="Donor location updated successfully.")


@router.delete(
    "/{id}/location",
    response_model=ApiResponse[DonorResponse],
    summary="Remove donor GPS coordinates",
)
async def remove_donor_location(
    id: int,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = DonorService(session)
    if current_user.role != UserRole.SUPER_ADMIN:
        existing = await service.get_donor_by_id(id)
        if existing.hospital_id is None or existing.hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException(
                f"Access denied. User belongs to hospital {current_user.hospital_id}, cannot manage donor with hospital {existing.hospital_id}."
            )

    donor = await service.remove_donor_location(id)
    return success_response(data=donor, message="Donor location removed successfully.")
