from datetime import date
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.enums import DonationStatus
from app.repositories.base_repository import BaseRepository
from app.schemas.donor import DonorListQuery


class DonorRepository(BaseRepository[Donor]):
    def __init__(self, session: AsyncSession):
        super().__init__(Donor, session)

    async def get_by_phone(self, phone: str) -> Optional[Donor]:
        stmt = select(Donor).where(Donor.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Donor]:
        stmt = select(Donor).where(Donor.donor_code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_donor_code(self) -> str:
        stmt = select(func.count(Donor.id))
        count = (await self.session.execute(stmt)).scalar_one() or 0
        return f"DON{count + 1:05d}"

    async def get_latest_donation_date(self, donor_id: int) -> Optional[date]:
        """Compute latest completed donation date dynamically from donation ledger."""
        stmt = (
            select(func.max(Donation.donation_date))
            .where(
                Donation.donor_id == donor_id,
                Donation.status == DonationStatus.COMPLETED,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_effective_last_donation_date(
        self, donor: Donor
    ) -> Tuple[Optional[date], Optional[str]]:
        """
        Determines the authoritative effective last donation date and provenance.
        - If a hospital-verified donation exists in the ledger, it is evaluated against self-reported date.
        - The more recent date governs cooldown.
        - Provenance distinguishes 'HOSPITAL_VERIFIED' vs 'SELF_REPORTED'.
        """
        verified_date = await self.get_latest_donation_date(donor.id)
        self_date = donor.last_donation_date

        if verified_date and self_date:
            if verified_date >= self_date:
                return verified_date, "HOSPITAL_VERIFIED"
            else:
                return self_date, donor.last_donation_date_source or "SELF_REPORTED"
        elif verified_date:
            return verified_date, "HOSPITAL_VERIFIED"
        elif self_date:
            return self_date, donor.last_donation_date_source or "SELF_REPORTED"
        elif getattr(donor, "last_donation_date_source", None) == "NEVER_DONATED":
            return None, "NEVER_DONATED"
        return None, None

    async def list_donors(
        self, query: DonorListQuery, include_inactive: bool = False
    ) -> Tuple[List[Donor], Dict[int, Optional[date]], int]:
        stmt = select(Donor)

        # By default, exclude soft-deleted/archived donors
        if not include_inactive:
            stmt = stmt.where(Donor.is_active == True)

        if query.search:
            search_pattern = f"%{query.search.strip()}%"
            stmt = stmt.where(
                or_(
                    Donor.full_name.ilike(search_pattern),
                    Donor.donor_code.ilike(search_pattern),
                    Donor.phone.ilike(search_pattern),
                    Donor.district.ilike(search_pattern),
                    Donor.panchayat.ilike(search_pattern),
                )
            )

        if query.blood_group:
            stmt = stmt.where(Donor.blood_group == query.blood_group)

        if query.district:
            stmt = stmt.where(func.lower(Donor.district) == query.district.lower().strip())

        if query.is_available is not None:
            stmt = stmt.where(Donor.is_available == query.is_available)

        if query.hospital_id:
            stmt = stmt.where(Donor.hospital_id == query.hospital_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        # Pagination and order
        offset = (query.page - 1) * query.page_size
        stmt = stmt.order_by(Donor.full_name.asc()).offset(offset).limit(query.page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        # Batch fetch latest donation dates for returned donor IDs
        donor_ids = [d.id for d in items]
        latest_dates: Dict[int, Optional[date]] = {}

        if donor_ids:
            date_stmt = (
                select(Donation.donor_id, func.max(Donation.donation_date))
                .where(
                    Donation.donor_id.in_(donor_ids),
                    Donation.status == DonationStatus.COMPLETED,
                )
                .group_by(Donation.donor_id)
            )
            date_results = await self.session.execute(date_stmt)
            for d_id, l_date in date_results.all():
                latest_dates[d_id] = l_date

        return items, latest_dates, total
