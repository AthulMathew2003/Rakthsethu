from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import DonationStatus, UserRole
from app.models.user import User
from app.schemas.common import PaginatedData
from app.schemas.donation import (
    DonationCreate,
    DonationListQuery,
    DonationResponse,
    DonationUpdate,
)
from app.services.donation_service import DonationService

router = APIRouter(prefix="/donations", tags=["Donations"])


@router.post(
    "",
    response_model=ApiResponse[DonationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record a new blood donation event",
)
async def create_donation(
    data: DonationCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.SUPER_ADMIN and data.hospital_id is None:
        data.hospital_id = current_user.hospital_id

    service = DonationService(session)
    donation = await service.create_donation(data)
    return success_response(data=donation, message="Donation recorded successfully.")


@router.get(
    "",
    response_model=ApiResponse[PaginatedData[DonationResponse]],
    summary="List and filter donation ledger records (Paginated)",
)
async def list_donations(
    donor_id: Optional[int] = Query(None, description="Filter by donor ID"),
    hospital_id: Optional[int] = Query(None, description="Filter by collecting hospital"),
    status: Optional[DonationStatus] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, description="Filter start donation date"),
    to_date: Optional[date] = Query(None, description="Filter end donation date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = DonationListQuery(
        donor_id=donor_id,
        hospital_id=hospital_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    service = DonationService(session)
    paginated_result = await service.list_donations(query)
    return success_response(data=paginated_result, message="Donations retrieved successfully.")


@router.get(
    "/{id}",
    response_model=ApiResponse[DonationResponse],
    summary="Get donation event details by ID",
)
async def get_donation(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DonationService(session)
    donation = await service.get_donation_by_id(id)
    return success_response(data=donation, message="Donation retrieved successfully.")


@router.patch(
    "/{id}",
    response_model=ApiResponse[DonationResponse],
    summary="Update donation status or details (e.g. mark scheduled donation as completed)",
)
async def update_donation(
    id: int,
    data: DonationUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = DonationService(session)
    updated_donation = await service.update_donation(id, data, current_user=current_user)
    return success_response(data=updated_donation, message="Donation updated successfully.")

