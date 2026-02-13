"""Extension management schemas."""


from pydantic import BaseModel, Field, field_validator


class ExtensionCreate(BaseModel):
    """Create a new extension."""

    extension: str = Field(min_length=1, max_length=20, description="Extension number")
    name: str = Field(min_length=1, max_length=100, description="Display name")
    password: str = Field(min_length=4, description="SIP password")
    email: str | None = Field(default=None, max_length=255)
    voicemail_enabled: bool = True
    voicemail_pin: str | None = Field(default=None, min_length=4, max_length=10)
    is_admin: bool = False

    @field_validator("extension")
    @classmethod
    def validate_extension(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Extension must contain only digits")
        return v

    @field_validator("voicemail_pin")
    @classmethod
    def validate_pin(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("Voicemail PIN must contain only digits")
        return v


class ExtensionUpdate(BaseModel):
    """Update an existing extension (all fields optional)."""

    name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=4)
    email: str | None = Field(default=None, max_length=255)
    voicemail_enabled: bool | None = None
    voicemail_pin: str | None = Field(default=None, min_length=4, max_length=10)
    is_admin: bool | None = None
    caller_id: str | None = Field(default=None, max_length=100)
    dnd_enabled: bool | None = None
    forward_enabled: bool | None = None
    forward_destination: str | None = Field(default=None, max_length=20)


class ExtensionResponse(BaseModel):
    """Extension details in API response."""

    extension: str
    name: str
    email: str | None = None
    registered: bool = False
    voicemail_enabled: bool = True
    is_admin: bool = False
    caller_id: str | None = None
    dnd_enabled: bool = False
    forward_enabled: bool = False
    forward_destination: str | None = None
