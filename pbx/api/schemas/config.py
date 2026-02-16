"""Configuration management schemas."""

from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ConfigUpdate(BaseModel):
    """Update system configuration."""

    section: str = Field(description="Config section to update (e.g. 'sip', 'rtp', 'logging')")
    values: dict[str, Any] = Field(description="Key-value pairs to update")


class SSLConfig(BaseModel):
    """SSL/TLS configuration."""

    enabled: bool = False
    cert_path: str | None = None
    key_path: str | None = None
    auto_generate: bool = False


class NetworkConfig(BaseModel):
    """Network configuration."""

    sip_port: int = Field(default=5060, ge=1024, le=65535)
    rtp_port_start: int = Field(default=10000, ge=1024, le=65535)
    rtp_port_end: int = Field(default=20000, ge=1024, le=65535)
    api_port: int = Field(default=9000, ge=1024, le=65535)
    bind_address: str = "0.0.0.0"

    @field_validator("rtp_port_end")
    @classmethod
    def validate_port_range(cls, v: int, info: ValidationInfo) -> int:
        start = info.data.get("rtp_port_start", 10000)
        if v <= start:
            raise ValueError("rtp_port_end must be greater than rtp_port_start")
        return v
