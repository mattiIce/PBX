"""
CallRecord ORM model for call detail records (CDR).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pbx.models.base import Base


class CallRecord(Base):
    """Represents a call detail record."""

    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    caller: Mapped[str] = mapped_column(String(50), nullable=False)
    callee: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    direction: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="inbound, outbound, or internal"
    )
    recording_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_call_records_call_id", "call_id"),
        Index("ix_call_records_caller", "caller"),
        Index("ix_call_records_callee", "callee"),
        Index("ix_call_records_start_time", "start_time"),
        Index("ix_call_records_direction", "direction"),
    )

    def __repr__(self) -> str:
        return (
            f"<CallRecord(id={self.id}, call_id='{self.call_id}', "
            f"caller='{self.caller}', callee='{self.callee}')>"
        )
