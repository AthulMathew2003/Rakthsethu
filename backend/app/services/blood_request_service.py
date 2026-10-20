import math
from typing import Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    DuplicateResourceException,
    HospitalAccessDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from app.models.blood_request import BloodRequest
from app.models.enums import RequestStatus, UserRole
from app.models.user import User
from app.repositories.blood_request_repository import BloodRequestRepository
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.blood_request import (
    BloodRequestCreate,
    BloodRequestListQuery,
    BloodRequestResponse,
    BloodRequestUpdate,
)
from app.schemas.common import PaginatedData
from app.schemas.matching import MatchDonorsRequest, MatchDonorsResponse
from app.services.matching_service import MatchingService

# Valid state transition matrix for blood requests
VALID_REQUEST_TRANSITIONS: Dict[RequestStatus, Set[RequestStatus]] = {
    RequestStatus.PENDING: {
        RequestStatus.PENDING,
        RequestStatus.IN_PROGRESS,
        RequestStatus.CANCELLED,
        RequestStatus.REJECTED,
    },
    RequestStatus.IN_PROGRESS: {
        RequestStatus.IN_PROGRESS,
        RequestStatus.FULFILLED,
        RequestStatus.CANCELLED,
        RequestStatus.REJECTED,
    },
    RequestStatus.FULFILLED: {
        RequestStatus.FULFILLED,  # Terminal state
    },
    RequestStatus.CANCELLED: {
        RequestStatus.CANCELLED,  # Terminal state
    },
    RequestStatus.REJECTED: {
        RequestStatus.REJECTED,  # Terminal state
    },
}


class BloodRequestService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.request_repo = BloodRequestRepository(session)
        self.hospital_repo = HospitalRepository(session)

    async def create_blood_request(self, data: BloodRequestCreate) -> BloodRequestResponse:
        hospital = await self.hospital_repo.get_by_id(data.hospital_id)
        if not hospital:
            raise ResourceNotFoundException("Hospital", data.hospital_id)

        if data.units_requested <= 0:
            raise ValidationException("units_requested must be greater than 0.")

        # Prevent creating directly in terminal states
        if data.status in (RequestStatus.FULFILLED, RequestStatus.CANCELLED, RequestStatus.REJECTED):
            raise ValidationException(f"Newly created blood request cannot start in terminal status '{data.status.value}'.")

        request_code = data.request_code
        if request_code:
            existing = await self.request_repo.get_by_code(request_code)
            if existing:
                raise DuplicateResourceException("BloodRequest", "request_code", request_code)
        else:
            request_code = await self.request_repo.generate_next_request_code()

        new_request = BloodRequest(
            request_code=request_code,
            hospital_id=data.hospital_id,
            patient_name=data.patient_name.strip(),
            blood_group=data.blood_group,
            units_requested=data.units_requested,
            district=data.district.strip(),
            location=data.location.strip() if data.location else None,
            contact_phone=data.contact_phone.strip(),
            emergency_contact=data.emergency_contact.strip() if data.emergency_contact else None,
            required_date=data.required_date,
            urgency=data.urgency,
            status=data.status,
            notes=data.notes.strip() if data.notes else None,
        )

        await self.request_repo.add(new_request)
        await self.session.commit()
        await self.session.refresh(new_request)

        resp = BloodRequestResponse.model_validate(new_request)
        resp.hospital_name = hospital.name
        return resp

    async def get_blood_request_by_id(self, request_id: int) -> BloodRequestResponse:
        req = await self.request_repo.get_by_id_with_hospital(request_id)
        if not req:
            raise ResourceNotFoundException("BloodRequest", request_id)

        resp = BloodRequestResponse.model_validate(req)
        if req.hospital:
            resp.hospital_name = req.hospital.name
        return resp

    async def update_blood_request(
        self, request_id: int, data: BloodRequestUpdate
    ) -> BloodRequestResponse:
        req = await self.request_repo.get_by_id_with_hospital(request_id)
        if not req:
            raise ResourceNotFoundException("BloodRequest", request_id)

        update_dict = data.model_dump(exclude_unset=True)

        # Validate units requested
        if "units_requested" in update_dict and update_dict["units_requested"] is not None:
            if update_dict["units_requested"] <= 0:
                raise ValidationException("units_requested must be greater than 0.")

        # Enforce valid state machine transitions
        if "status" in update_dict and update_dict["status"] is not None:
            target_status = update_dict["status"]
            allowed_next = VALID_REQUEST_TRANSITIONS.get(req.status, {req.status})
            if target_status not in allowed_next:
                raise ValidationException(
                    f"Invalid blood request state transition from '{req.status.value}' to '{target_status.value}'. "
                    f"Terminal states cannot be mutated and requests must progress through PENDING -> IN_PROGRESS -> FULFILLED."
                )

        for key, value in update_dict.items():
            if value is not None and isinstance(value, str):
                setattr(req, key, value.strip())
            else:
                setattr(req, key, value)

        await self.session.commit()
        await self.session.refresh(req)

        resp = BloodRequestResponse.model_validate(req)
        if req.hospital:
            resp.hospital_name = req.hospital.name
        return resp

    async def list_blood_requests(
        self, query: BloodRequestListQuery
    ) -> PaginatedData[BloodRequestResponse]:
        items, total = await self.request_repo.list_blood_requests(query)
        total_pages = math.ceil(total / query.page_size) if total > 0 else 1

        response_items = []
        for req in items:
            resp = BloodRequestResponse.model_validate(req)
            if req.hospital:
                resp.hospital_name = req.hospital.name
            response_items.append(resp)

        return PaginatedData(
            items=response_items,
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_matches_for_request(
        self,
        request_id: int,
        current_user: User,
        limit: int = 20,
    ) -> MatchDonorsResponse:
        """
        Integrates with MatchingService to find eligible donors for a specific blood request.
        Enforces hospital scoping and ensures only active (PENDING/IN_PROGRESS) requests can be matched.
        """
        req = await self.request_repo.get_by_id_with_hospital(request_id)
        if not req:
            raise ResourceNotFoundException("BloodRequest", request_id)

        # Enforce RBAC hospital scoping
        if current_user.role != UserRole.SUPER_ADMIN:
            if req.hospital_id != current_user.hospital_id:
                raise HospitalAccessDeniedException("Access denied to another hospital's blood request.")

        # Validate request state eligibility for matching
        if req.status not in (RequestStatus.PENDING, RequestStatus.IN_PROGRESS):
            raise ValidationException(
                f"Cannot find donor matches for blood request in '{req.status.value}' status. "
                "Only PENDING and IN_PROGRESS requests can be actively matched."
            )

        matching_service = MatchingService(self.session)
        matching_req = MatchDonorsRequest(
            blood_group=req.blood_group,
            district=req.district,
            panchayat=req.location,
            hospital_id=req.hospital_id,
            required_units=req.units_requested,
            required_date=req.required_date,
            limit=limit,
        )

        return await matching_service.find_matching_donors(request=matching_req)
