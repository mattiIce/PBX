"""
RegisteredPhone ORM model for tracking SIP phone registrations.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pbx.models.base import Base


class RegisteredPhone(Base):
    """Represents a registered SIP phone device."""

    __tablename__ = "registered_phones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(20), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_registered_phones_extension", "extension"),
        Index("ix_registered_phones_ip_address", "ip_address"),
        Index("ix_registered_phones_mac_address", "mac_address"),
    )

    def __repr__(self) -> str:
        return (
            f"<RegisteredPhone(id={self.id}, extension='{self.extension}', "
            f"ip_address='{self.ip_address}', mac_address='{self.mac_address}')>"
        )
