"""Add sip_password field to extensions table for SIP digest authentication.

Revision ID: 002
Revises: 001
Create Date: 2026-02-24

This migration adds support for storing SIP-specific passwords, which are used
for phone provisioning and SIP digest authentication. The sip_password is
separate from the user's login password_hash and is displayed to phones
during provisioning.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add sip_password column to extensions table."""
    from sqlalchemy import inspect as sa_inspect

    # Check if column already exists
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("extensions")]

    if "sip_password" not in columns:
        op.add_column(
            "extensions",
            sa.Column("sip_password", sa.String(255), nullable=True),
        )


def downgrade() -> None:
    """Remove sip_password column from extensions table."""
    from sqlalchemy import inspect as sa_inspect

    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("extensions")]

    if "sip_password" in columns:
        op.drop_column("extensions", "sip_password")
