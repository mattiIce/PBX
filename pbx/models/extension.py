"""
Extension ORM model for PBX users/extensions.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from pbx.models.base import Base, TimestampMixin


class Extension(TimestampMixin, Base):
    """Represents a PBX extension (user line)."""

    __tablename__ = "extensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voicemail_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    voicemail_pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    caller_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dnd_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    forward_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    forward_destination: Mapped[str | None] = mapped_column(String(50), nullable=True)
    allow_external: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    ad_synced: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    registered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_extensions_number", "number"),
        Index("ix_extensions_email", "email"),
        Index("ix_extensions_ad_synced", "ad_synced"),
    )

    def __repr__(self) -> str:
        return f"<Extension(id={self.id}, number='{self.number}', name='{self.name}')>"
