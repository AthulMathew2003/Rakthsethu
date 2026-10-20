from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import check_hospital_scope, get_current_user, require_role
from app.core.response import ApiResponse, success_response
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.matching import MatchDonorsRequest, MatchDonorsResponse
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/matching", tags=["Donor Matching Engine"])


@router.post(
    "/donors",
    response_model=ApiResponse[MatchDonorsResponse],
    summary="Search and rank eligible blood donors for a recipient blood request",
)
async def match_donors(
    data: MatchDonorsRequest,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    """
    Evaluates ABO/Rh blood compatibility, active/availability flags, geographic location,
    and donation cooldown periods to return a ranked list of eligible blood donors.
    """
    if current_user.role != UserRole.SUPER_ADMIN and data.hospital_id is not None:
        check_hospital_scope(current_user, data.hospital_id)
    service = MatchingService(session)
    result = await service.find_matching_donors(request=data)
    loc_desc = (
        f"{result.origin_type} ({result.radius_km}km)"
        if result.origin_type != "DISTRICT_DEFAULT"
        else f"{result.district or 'target area'}"
    )
    return success_response(
        data=result,
        message=f"Found {result.total_eligible_found} eligible donors matching {data.blood_group.value} in {loc_desc}.",
    )
