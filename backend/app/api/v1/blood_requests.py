from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import check_hospital_scope, get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency, UserRole
from app.models.user import User
from app.schemas.blood_request import (
    BloodRequestCreate,
    BloodRequestListQuery,
    BloodRequestResponse,
    BloodRequestUpdate,
)
from app.schemas.common import PaginatedData
from app.schemas.matching import MatchDonorsResponse
from app.services.blood_request_service import BloodRequestService

router = APIRouter(prefix="/blood-requests", tags=["Blood Requests"])


@router.post(
    "",
    response_model=ApiResponse[BloodRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new clinical blood request",
)
async def create_blood_request(
    data: BloodRequestCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.SUPER_ADMIN and data.hospital_id is None:
        data.hospital_id = current_user.hospital_id
    elif current_user.role != UserRole.SUPER_ADMIN:
        check_hospital_scope(current_user, data.hospital_id)

    service = BloodRequestService(session)
    req = await service.create_blood_request(data)
    return success_response(data=req, message="Blood request created successfully.")


@router.get(
    "",
    response_model=ApiResponse[PaginatedData[BloodRequestResponse]],
    summary="List and filter blood requests (Paginated)",
)
async def list_blood_requests(
    hospital_id: Optional[int] = Query(None, description="Filter by hospital"),
    blood_group: Optional[BloodGroup] = Query(None, description="Filter by blood group"),
    district: Optional[str] = Query(None, description="Filter by district"),
    urgency: Optional[RequestUrgency] = Query(None, description="Filter by urgency"),
    request_status: Optional[RequestStatus] = Query(None, alias="status", description="Filter by request status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    query = BloodRequestListQuery(
        hospital_id=hospital_id,
        blood_group=blood_group,
        district=district,
        urgency=urgency,
        status=request_status,
        page=page,
        page_size=page_size,
    )
    service = BloodRequestService(session)
    paginated_result = await service.list_blood_requests(query)
    return success_response(data=paginated_result, message="Blood requests retrieved successfully.")


@router.get(
    "/{id}",
    response_model=ApiResponse[BloodRequestResponse],
    summary="Get blood request details by ID",
)
async def get_blood_request(
    id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = BloodRequestService(session)
    req = await service.get_blood_request_by_id(id)
    return success_response(data=req, message="Blood request retrieved successfully.")


@router.patch(
    "/{id}",
    response_model=ApiResponse[BloodRequestResponse],
    summary="Update blood request status or details",
)
async def update_blood_request(
    id: int,
    data: BloodRequestUpdate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = BloodRequestService(session)
    # Check hospital scope before update if user is hospital staff
    if current_user.role != UserRole.SUPER_ADMIN:
        existing = await service.get_blood_request_by_id(id)
        check_hospital_scope(current_user, existing.hospital_id)

    updated_req = await service.update_blood_request(id, data)
    return success_response(data=updated_req, message="Blood request updated successfully.")


@router.get(
    "/{id}/matches",
    response_model=ApiResponse[MatchDonorsResponse],
    summary="Find matching eligible blood donors for a specific blood request",
)
async def get_matches_for_blood_request(
    id: int,
    limit: int = Query(20, ge=1, le=100, description="Max eligible donors to return"),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    service = BloodRequestService(session)
    matches = await service.get_matches_for_request(request_id=id, current_user=current_user, limit=limit)
    return success_response(
        data=matches,
        message=f"Found {matches.total_eligible_found} eligible donors for blood request #{id}.",
    )
