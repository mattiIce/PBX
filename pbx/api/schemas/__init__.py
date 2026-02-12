"""Pydantic schemas for API request/response validation."""

from pbx.api.schemas.auth import LoginRequest, LoginResponse
from pbx.api.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from pbx.api.schemas.extensions import ExtensionCreate, ExtensionResponse, ExtensionUpdate

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "ExtensionCreate",
    "ExtensionUpdate",
    "ExtensionResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "SuccessResponse",
]
