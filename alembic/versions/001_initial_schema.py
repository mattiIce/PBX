"""Initial schema - create all PBX tables.

Revision ID: 001
Revises:
Create Date: 2026-02-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- extensions table ----
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
    op.create_index("ix_extensions_number", "extensions", ["number"])
    op.create_index("ix_extensions_email", "extensions", ["email"])
    op.create_index("ix_extensions_ad_synced", "extensions", ["ad_synced"])

    # ---- call_records table ----
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
    op.create_index("ix_call_records_call_id", "call_records", ["call_id"])
    op.create_index("ix_call_records_caller", "call_records", ["caller"])
    op.create_index("ix_call_records_callee", "call_records", ["callee"])
    op.create_index("ix_call_records_start_time", "call_records", ["start_time"])
    op.create_index("ix_call_records_direction", "call_records", ["direction"])

    # ---- voicemails table ----
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
    op.create_index("ix_voicemails_extension", "voicemails", ["extension"])
    op.create_index("ix_voicemails_listened", "voicemails", ["listened"])
    op.create_index("ix_voicemails_timestamp", "voicemails", ["timestamp"])

    # ---- registered_phones table ----
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
    op.create_index("ix_registered_phones_extension", "registered_phones", ["extension"])
    op.create_index("ix_registered_phones_ip_address", "registered_phones", ["ip_address"])
    op.create_index("ix_registered_phones_mac_address", "registered_phones", ["mac_address"])


def downgrade() -> None:
    op.drop_table("registered_phones")
    op.drop_table("voicemails")
    op.drop_table("call_records")
    op.drop_table("extensions")
