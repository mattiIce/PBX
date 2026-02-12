"""Authentication request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    """Login request payload."""

    extension: str = Field(min_length=1, max_length=20, description="Extension number")
    password: str = Field(min_length=1, description="Extension password")

    @field_validator("extension")
    @classmethod
    def validate_extension(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Extension must contain only digits")
        return v


class LoginResponse(BaseModel):
    """Login response payload."""

    token: str
    extension: str
    name: Optional[str] = None
    is_admin: bool = False
    expires_in: int = Field(default=86400, description="Token TTL in seconds")


class LogoutResponse(BaseModel):
    """Logout response payload."""

    success: bool = True
    message: str = "Logged out successfully"
