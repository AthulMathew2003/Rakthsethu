from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedData(BaseModel, Generic[ItemT]):
    items: List[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int
