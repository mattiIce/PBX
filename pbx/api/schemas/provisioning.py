"""Provisioning and phone registration schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProvisionDevice(BaseModel):
    """Provision a new phone device."""

    mac_address: str = Field(min_length=12, max_length=17, description="Device MAC address")
    model: str = Field(min_length=1, max_length=100, description="Phone model")
    extension: str = Field(min_length=1, max_length=20, description="Assigned extension")
    template: Optional[str] = Field(default=None, description="Provisioning template name")
    label: Optional[str] = Field(default=None, max_length=100)

    @field_validator("mac_address")
    @classmethod
    def normalize_mac(cls, v: str) -> str:
        # Strip separators and normalize to uppercase
        normalized = v.replace(":", "").replace("-", "").replace(".", "").upper()
        if len(normalized) != 12 or not all(c in "0123456789ABCDEF" for c in normalized):
            raise ValueError("Invalid MAC address format")
        return normalized


class RegisterPhone(BaseModel):
    """Register a phone."""

    mac_address: str = Field(min_length=12, max_length=17)
    ip_address: str = Field(description="Phone IP address")
    extension: str = Field(min_length=1, max_length=20)
    model: Optional[str] = Field(default=None, max_length=100)
    firmware: Optional[str] = Field(default=None, max_length=50)


class ProvisioningTemplate(BaseModel):
    """Provisioning template definition."""

    name: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=100)
    model_pattern: Optional[str] = Field(default=None, max_length=100)
    template_content: str = Field(description="Template body (supports variables)")
    content_type: str = Field(default="text/xml", max_length=50)
