from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.blood_request import BloodRequest
from app.models.hospital import Hospital
from app.repositories.base_repository import BaseRepository
from app.schemas.blood_request import BloodRequestListQuery


class BloodRequestRepository(BaseRepository[BloodRequest]):
    def __init__(self, session: AsyncSession):
        super().__init__(BloodRequest, session)

    async def get_by_code(self, code: str) -> Optional[BloodRequest]:
        stmt = (
            select(BloodRequest)
            .options(joinedload(BloodRequest.hospital))
            .where(BloodRequest.request_code == code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_hospital(self, id: int) -> Optional[BloodRequest]:
        stmt = (
            select(BloodRequest)
            .options(joinedload(BloodRequest.hospital))
            .where(BloodRequest.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_request_code(self) -> str:
        stmt = select(func.count(BloodRequest.id))
        count = (await self.session.execute(stmt)).scalar_one() or 0
        return f"BR{count + 1:05d}"

    async def list_blood_requests(
        self, query: BloodRequestListQuery
    ) -> Tuple[List[BloodRequest], int]:
        stmt = select(BloodRequest).options(joinedload(BloodRequest.hospital))

        if query.hospital_id:
            stmt = stmt.where(BloodRequest.hospital_id == query.hospital_id)

        if query.blood_group:
            stmt = stmt.where(BloodRequest.blood_group == query.blood_group)

        if query.district:
            stmt = stmt.where(func.lower(BloodRequest.district) == query.district.lower().strip())

        if query.urgency:
            stmt = stmt.where(BloodRequest.urgency == query.urgency)

        if query.status:
            stmt = stmt.where(BloodRequest.status == query.status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        # Pagination and order
        offset = (query.page - 1) * query.page_size
        stmt = (
            stmt.order_by(BloodRequest.required_date.asc(), BloodRequest.id.desc())
            .offset(offset)
            .limit(query.page_size)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
