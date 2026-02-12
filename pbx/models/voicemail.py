"""
Voicemail ORM model for voicemail messages.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from pbx.models.base import Base


class Voicemail(Base):
    """Represents a voicemail message."""

    __tablename__ = "voicemails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    caller_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), nullable=False
    )
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    listened: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    audio_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transcription_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcription_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_voicemails_extension", "extension"),
        Index("ix_voicemails_listened", "listened"),
        Index("ix_voicemails_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<Voicemail(id={self.id}, extension='{self.extension}', "
            f"caller_id='{self.caller_id}', listened={self.listened})>"
        )
