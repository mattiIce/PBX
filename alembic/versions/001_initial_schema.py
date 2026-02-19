"""Dual Migration Mechanism
==========================

The PBX system uses two complementary mechanisms for database table management:

1. **Alembic migrations** (this directory) manage the 4 core tables:
   - extensions, call_records, voicemails, registered_phones
   These tables are versioned here and follow a strict upgrade/downgrade path.

2. **Runtime migrations** (pbx/utils/migrations.py) manage feature module tables
   using idempotent CREATE TABLE IF NOT EXISTS statements. Feature modules create
   their own tables on startup, so they do not require Alembic migrations.

Creating new Alembic migrations:
- Create a new migration for any schema change to the core tables listed above.
- Generate with: alembic revision -m "description"
- Always implement both upgrade() and downgrade() functions.
- Test round-trip: alembic upgrade head && alembic downgrade -1 && alembic upgrade head

Do NOT create retroactive Alembic migrations for feature module tables; they use
idempotent CREATE TABLE IF NOT EXISTS and are managed at runtime.
"""

"""Initial schema - create all PBX tables.

Revision ID: 001
Revises:
Create Date: 2026-02-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    return table_name in inspector.get_table_names()


def _index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index already exists on a table."""
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    # ---- extensions table ----
    if not _table_exists("extensions"):
        op.create_table(
            "extensions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("number", sa.String(20), unique=True, nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("voicemail_enabled", sa.Boolean, server_default="1", nullable=False),
            sa.Column("voicemail_pin_hash", sa.String(255), nullable=True),
            sa.Column("is_admin", sa.Boolean, server_default="0", nullable=False),
            sa.Column("caller_id", sa.String(50), nullable=True),
            sa.Column("dnd_enabled", sa.Boolean, server_default="0", nullable=False),
            sa.Column("forward_enabled", sa.Boolean, server_default="0", nullable=False),
            sa.Column("forward_destination", sa.String(50), nullable=True),
            sa.Column("allow_external", sa.Boolean, server_default="1", nullable=False),
            sa.Column("ad_synced", sa.Boolean, server_default="0", nullable=False),
            sa.Column("registered", sa.Boolean, server_default="0", nullable=False),
            sa.Column("registered_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
    if not _index_exists("ix_extensions_number", "extensions"):
        op.create_index("ix_extensions_number", "extensions", ["number"])
    if not _index_exists("ix_extensions_email", "extensions"):
        op.create_index("ix_extensions_email", "extensions", ["email"])
    if not _index_exists("ix_extensions_ad_synced", "extensions"):
        op.create_index("ix_extensions_ad_synced", "extensions", ["ad_synced"])

    # ---- call_records table ----
    if not _table_exists("call_records"):
        op.create_table(
            "call_records",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("call_id", sa.String(100), unique=True, nullable=False),
            sa.Column("caller", sa.String(50), nullable=False),
            sa.Column("callee", sa.String(50), nullable=False),
            sa.Column("start_time", sa.DateTime, nullable=True),
            sa.Column("end_time", sa.DateTime, nullable=True),
            sa.Column("duration", sa.Integer, nullable=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column(
                "direction",
                sa.String(20),
                nullable=True,
                comment="inbound, outbound, or internal",
            ),
            sa.Column("recording_path", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
    if not _index_exists("ix_call_records_call_id", "call_records"):
        op.create_index("ix_call_records_call_id", "call_records", ["call_id"])
    if not _index_exists("ix_call_records_caller", "call_records"):
        op.create_index("ix_call_records_caller", "call_records", ["caller"])
    if not _index_exists("ix_call_records_callee", "call_records"):
        op.create_index("ix_call_records_callee", "call_records", ["callee"])
    if not _index_exists("ix_call_records_start_time", "call_records"):
        op.create_index("ix_call_records_start_time", "call_records", ["start_time"])
    if not _index_exists("ix_call_records_direction", "call_records"):
        op.create_index("ix_call_records_direction", "call_records", ["direction"])

    # ---- voicemails table ----
    if not _table_exists("voicemails"):
        op.create_table(
            "voicemails",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("extension", sa.String(20), nullable=False),
            sa.Column("caller_id", sa.String(50), nullable=True),
            sa.Column("timestamp", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("duration", sa.Integer, nullable=True),
            sa.Column("listened", sa.Boolean, server_default="0", nullable=False),
            sa.Column("audio_path", sa.String(255), nullable=True),
            sa.Column("transcription_text", sa.Text, nullable=True),
            sa.Column("transcription_confidence", sa.Float, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
    if not _index_exists("ix_voicemails_extension", "voicemails"):
        op.create_index("ix_voicemails_extension", "voicemails", ["extension"])
    if not _index_exists("ix_voicemails_listened", "voicemails"):
        op.create_index("ix_voicemails_listened", "voicemails", ["listened"])
    if not _index_exists("ix_voicemails_timestamp", "voicemails"):
        op.create_index("ix_voicemails_timestamp", "voicemails", ["timestamp"])

    # ---- registered_phones table ----
    if not _table_exists("registered_phones"):
        op.create_table(
            "registered_phones",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("extension", sa.String(20), nullable=False),
            sa.Column("ip_address", sa.String(50), nullable=False),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column("mac_address", sa.String(20), nullable=True),
            sa.Column("registered_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("expires_at", sa.DateTime, nullable=True),
        )
    if not _index_exists("ix_registered_phones_extension", "registered_phones"):
        op.create_index("ix_registered_phones_extension", "registered_phones", ["extension"])
    if not _index_exists("ix_registered_phones_ip_address", "registered_phones"):
        op.create_index("ix_registered_phones_ip_address", "registered_phones", ["ip_address"])
    if not _index_exists("ix_registered_phones_mac_address", "registered_phones"):
        op.create_index("ix_registered_phones_mac_address", "registered_phones", ["mac_address"])


def downgrade() -> None:
    op.drop_table("registered_phones")
    op.drop_table("voicemails")
    op.drop_table("call_records")
    op.drop_table("extensions")
