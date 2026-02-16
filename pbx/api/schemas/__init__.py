"""Pydantic schemas for API request/response validation."""

from pbx.api.schemas.auth import LoginRequest, LoginResponse, LogoutResponse
from pbx.api.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from pbx.api.schemas.extensions import ExtensionCreate, ExtensionResponse, ExtensionUpdate

__all__ = [
    "ErrorResponse",
    "ExtensionCreate",
    "ExtensionResponse",
    "ExtensionUpdate",
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    "PaginatedResponse",
    "SuccessResponse",
]
