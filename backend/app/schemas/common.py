"""Common schemas for API responses."""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List, Any, Dict

from pydantic import BaseModel, Field

T = TypeVar("T")


def model_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert any model object to dict with fallback.

    Handles:
    - Objects with to_dict() method
    - Objects with __dict__ attribute (filters private attributes)
    - Dicts passed through
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {}


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page * page_size < total,
            has_prev=page > 1,
        )


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: str
    code: Optional[str] = None
    detail: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)
