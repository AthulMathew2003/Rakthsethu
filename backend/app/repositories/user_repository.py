from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_code(self, user_code: str) -> Optional[User]:
        stmt = select(User).where(User.user_code == user_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_next_user_code(self) -> str:
        stmt = select(func.count(User.id))
        count = (await self.session.execute(stmt)).scalar_one() or 0
        return f"USR{count + 1:04d}"
