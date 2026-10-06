from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.donation import Donation
from app.models.donor import Donor
from app.repositories.base_repository import BaseRepository
from app.schemas.donation import DonationListQuery


class DonationRepository(BaseRepository[Donation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Donation, session)

    async def get_by_code(self, code: str) -> Optional[Donation]:
        stmt = (
            select(Donation)
            .options(joinedload(Donation.donor))
            .where(Donation.donation_code == code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_donor(self, id: int) -> Optional[Donation]:
        stmt = (
            select(Donation)
            .options(joinedload(Donation.donor))
            .where(Donation.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_donation_code(self) -> str:
        stmt = select(func.count(Donation.id))
        count = (await self.session.execute(stmt)).scalar_one() or 0
        return f"DN{count + 1:05d}"

    async def list_donations(self, query: DonationListQuery) -> Tuple[List[Donation], int]:
        stmt = select(Donation).options(joinedload(Donation.donor))

        if query.donor_id:
            stmt = stmt.where(Donation.donor_id == query.donor_id)

        if query.hospital_id:
            stmt = stmt.where(Donation.hospital_id == query.hospital_id)

        if query.status:
            stmt = stmt.where(Donation.status == query.status)

        if query.from_date:
            stmt = stmt.where(Donation.donation_date >= query.from_date)

        if query.to_date:
            stmt = stmt.where(Donation.donation_date <= query.to_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        # Pagination and order
        offset = (query.page - 1) * query.page_size
        stmt = (
            stmt.order_by(Donation.donation_date.desc(), Donation.id.desc())
            .offset(offset)
            .limit(query.page_size)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
