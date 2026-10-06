from datetime import date
import math
from typing import Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    DuplicateResourceException,
    HospitalAccessDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from app.models.donation import Donation
from app.models.enums import DonationStatus, UserRole
from app.models.user import User
from app.repositories.donation_repository import DonationRepository
from app.repositories.donor_repository import DonorRepository
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.common import PaginatedData
from app.schemas.donation import DonationCreate, DonationListQuery, DonationResponse, DonationUpdate
from app.services.cooldown_service import calculate_cooldown_eligibility

# Valid state transitions for donation records
VALID_DONATION_TRANSITIONS: Dict[DonationStatus, Set[DonationStatus]] = {
    DonationStatus.SCHEDULED: {
        DonationStatus.SCHEDULED,
        DonationStatus.COMPLETED,
        DonationStatus.CANCELLED,
        DonationStatus.REJECTED,
    },
    DonationStatus.COMPLETED: {
        DonationStatus.COMPLETED,  # Terminal state
    },
    DonationStatus.CANCELLED: {
        DonationStatus.CANCELLED,  # Terminal state
    },
    DonationStatus.REJECTED: {
        DonationStatus.REJECTED,  # Terminal state
    },
}


class DonationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.donation_repo = DonationRepository(session)
        self.donor_repo = DonorRepository(session)
        self.hospital_repo = HospitalRepository(session)

    async def create_donation(self, data: DonationCreate, current_user: Optional[User] = None) -> DonationResponse:
        donor = await self.donor_repo.get_by_id(data.donor_id)
        if not donor:
            raise ResourceNotFoundException("Donor", data.donor_id)

        if not donor.is_active:
            raise ValidationException(f"Cannot record donation for inactive donor '{donor.full_name}' ({donor.donor_code}).")

        if data.hospital_id:
            hospital = await self.hospital_repo.get_by_id(data.hospital_id)
            if not hospital:
                raise ResourceNotFoundException("Hospital", data.hospital_id)

        if data.units_donated <= 0:
            raise ValidationException("units_donated must be greater than 0.")

        # Date validation for COMPLETED donations
        if data.status == DonationStatus.COMPLETED and data.donation_date > date.today():
            raise ValidationException("A completed donation cannot have a future donation date.")

        # Cooldown validation when recording a new completed donation
        if data.status == DonationStatus.COMPLETED:
            latest_prev_date = await self.donor_repo.get_latest_donation_date(data.donor_id)
            if latest_prev_date and latest_prev_date <= data.donation_date:
                cooldown = calculate_cooldown_eligibility(
                    last_donation_date=latest_prev_date,
                    donation_type=data.donation_type,
                    reference_date=data.donation_date,
                )
                if not cooldown.is_eligible:
                    raise ValidationException(
                        f"Donor '{donor.full_name}' is currently on cooldown until {cooldown.eligible_from} "
                        f"({cooldown.days_remaining} days remaining). Cannot record a completed donation before the rest period expires."
                    )

        donation_code = data.donation_code
        if donation_code:
            existing = await self.donation_repo.get_by_code(donation_code)
            if existing:
                raise DuplicateResourceException("Donation", "donation_code", donation_code)
        else:
            donation_code = await self.donation_repo.generate_next_donation_code()

        new_donation = Donation(
            donation_code=donation_code,
            donor_id=data.donor_id,
            hospital_id=data.hospital_id,
            donation_date=data.donation_date,
            donation_type=data.donation_type.strip(),
            units_donated=data.units_donated,
            status=data.status,
            notes=data.notes.strip() if data.notes else None,
        )

        await self.donation_repo.add(new_donation)
        await self.session.commit()
        await self.session.refresh(new_donation)

        resp = DonationResponse.model_validate(new_donation)
        resp.donor_name = donor.full_name
        resp.donor_blood_group = donor.blood_group.value
        return resp

    async def get_donation_by_id(self, donation_id: int) -> DonationResponse:
        donation = await self.donation_repo.get_by_id_with_donor(donation_id)
        if not donation:
            raise ResourceNotFoundException("Donation", donation_id)

        resp = DonationResponse.model_validate(donation)
        if donation.donor:
            resp.donor_name = donation.donor.full_name
            resp.donor_blood_group = donation.donor.blood_group.value
        return resp

    async def update_donation(
        self, donation_id: int, data: DonationUpdate, current_user: User
    ) -> DonationResponse:
        donation = await self.donation_repo.get_by_id_with_donor(donation_id)
        if not donation:
            raise ResourceNotFoundException("Donation", donation_id)

        # Enforce RBAC hospital scoping
        if current_user.role != UserRole.SUPER_ADMIN:
            if donation.hospital_id and donation.hospital_id != current_user.hospital_id:
                raise HospitalAccessDeniedException("Access denied to update another hospital's donation record.")

        update_dict = data.model_dump(exclude_unset=True)

        # Enforce valid state machine transitions
        if "status" in update_dict and update_dict["status"] is not None:
            target_status = update_dict["status"]
            allowed_next = VALID_DONATION_TRANSITIONS.get(donation.status, {donation.status})
            if target_status not in allowed_next:
                raise ValidationException(
                    f"Invalid donation state transition from '{donation.status.value}' to '{target_status.value}'. "
                    f"Completed donations cannot be reversed or rescheduled."
                )

            # If transitioning to COMPLETED, validate date
            if target_status == DonationStatus.COMPLETED:
                effective_date = update_dict.get("donation_date") or donation.donation_date
                if effective_date > date.today():
                    raise ValidationException("A completed donation cannot have a future donation date.")

        if "units_donated" in update_dict and update_dict["units_donated"] is not None:
            if update_dict["units_donated"] <= 0:
                raise ValidationException("units_donated must be greater than 0.")

        for key, value in update_dict.items():
            if value is not None and isinstance(value, str):
                setattr(donation, key, value.strip())
            else:
                setattr(donation, key, value)

        await self.session.commit()
        await self.session.refresh(donation)

        resp = DonationResponse.model_validate(donation)
        if donation.donor:
            resp.donor_name = donation.donor.full_name
            resp.donor_blood_group = donation.donor.blood_group.value
        return resp

    async def list_donations(self, query: DonationListQuery) -> PaginatedData[DonationResponse]:
        items, total = await self.donation_repo.list_donations(query)
        total_pages = math.ceil(total / query.page_size) if total > 0 else 1

        response_items = []
        for d in items:
            resp = DonationResponse.model_validate(d)
            if d.donor:
                resp.donor_name = d.donor.full_name
                resp.donor_blood_group = d.donor.blood_group.value
            response_items.append(resp)

        return PaginatedData(
            items=response_items,
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        )
