from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ApiResponse, success_response
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Evaluates ABO/Rh blood compatibility, active/availability flags, geographic location,
    and donation cooldown periods to return a ranked list of eligible blood donors.
    """
    service = MatchingService(session)
    result = await service.find_matching_donors(request=data)
    return success_response(
        data=result,
        message=f"Found {result.total_eligible_found} eligible donors matching {data.blood_group.value} in {data.district}.",
    )
