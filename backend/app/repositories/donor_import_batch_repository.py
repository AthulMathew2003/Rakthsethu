from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.donor_import_batch import DonorImportBatch
from app.repositories.base_repository import BaseRepository


class DonorImportBatchRepository(BaseRepository[DonorImportBatch]):
    def __init__(self, session: AsyncSession):
        super().__init__(DonorImportBatch, session)

    async def get_by_code(self, batch_code: str) -> Optional[DonorImportBatch]:
        stmt = select(DonorImportBatch).where(DonorImportBatch.batch_code == batch_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_batch_code(self) -> str:
        stmt = select(func.count(DonorImportBatch.id))
        result = await self.session.execute(stmt)
        count = result.scalar_one() or 0
        return f"BATCH-{count + 1:05d}"

    async def list_batches(
        self,
        hospital_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[DonorImportBatch], int]:
        stmt = select(DonorImportBatch)
        count_stmt = select(func.count(DonorImportBatch.id))

        if hospital_id is not None:
            stmt = stmt.where(DonorImportBatch.hospital_id == hospital_id)
            count_stmt = count_stmt.where(DonorImportBatch.hospital_id == hospital_id)

        # Count total
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Paginate ordered by created_at desc
        offset = (page - 1) * page_size
        stmt = stmt.order_by(DonorImportBatch.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
