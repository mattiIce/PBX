"""Common response schemas shared across API endpoints."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    status: int = Field(description="HTTP status code")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated list response."""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False
