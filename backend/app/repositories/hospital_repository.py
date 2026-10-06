from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.hospital import Hospital
from app.repositories.base_repository import BaseRepository
from app.schemas.hospital import HospitalListQuery


class HospitalRepository(BaseRepository[Hospital]):
    def __init__(self, session: AsyncSession):
        super().__init__(Hospital, session)

    async def get_by_code(self, code: str) -> Optional[Hospital]:
        stmt = select(Hospital).where(Hospital.hospital_code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_hospital_code(self) -> str:
        stmt = select(func.count(Hospital.id))
        count = (await self.session.execute(stmt)).scalar_one() or 0
        return f"HOSP{count + 1:04d}"

    async def list_hospitals(self, query: HospitalListQuery) -> Tuple[List[Hospital], int]:
        stmt = select(Hospital)

        if query.search:
            search_pattern = f"%{query.search.strip()}%"
            stmt = stmt.where(
                or_(
                    Hospital.name.ilike(search_pattern),
                    Hospital.hospital_code.ilike(search_pattern),
                    Hospital.district.ilike(search_pattern),
                    Hospital.address.ilike(search_pattern),
                )
            )

        if query.district:
            stmt = stmt.where(func.lower(Hospital.district) == query.district.lower().strip())

        if query.is_active is not None:
            stmt = stmt.where(Hospital.is_active == query.is_active)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        # Pagination and order
        offset = (query.page - 1) * query.page_size
        stmt = stmt.order_by(Hospital.name.asc()).offset(offset).limit(query.page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
