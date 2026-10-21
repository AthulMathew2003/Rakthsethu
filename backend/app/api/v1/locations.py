from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, status

from app.core.location_service import get_districts, get_local_bodies
from app.core.response import ApiResponse, success_response

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    "/districts",
    response_model=ApiResponse[List[str]],
    summary="Get all 14 official districts of Kerala",
)
async def list_kerala_districts() -> ApiResponse[List[str]]:
    """Returns the alphabetical list of all 14 official districts of Kerala."""
    districts = get_districts()
    return success_response(
        data=districts,
        message="Kerala districts retrieved successfully.",
    )


@router.get(
    "/local-bodies",
    response_model=ApiResponse[List[Dict[str, Any]]],
    summary="Get all local bodies (Grama Panchayats, Municipalities, Corporations) for a Kerala district",
)
async def list_local_bodies(
    district: str = Query(..., description="Kerala district name (e.g. Kottayam, Ernakulam)"),
    search: Optional[str] = Query(None, description="Optional search term to filter local bodies"),
) -> ApiResponse[List[Dict[str, Any]]]:
    """
    Returns the list of local bodies belonging to the specified Kerala district,
    filtered by optional search query.
    """
    local_bodies = get_local_bodies(district=district, search=search)
    return success_response(
        data=local_bodies,
        message=f"Local bodies for {district} retrieved successfully.",
    )
