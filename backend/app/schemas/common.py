from pydantic import BaseModel
from typing import TypeVar, Generic, List, Optional

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


def paginate(query, page: int, page_size: int):
    """Helper: applies offset/limit to a SQLAlchemy query and returns pagination info."""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size
    return items, total, total_pages
