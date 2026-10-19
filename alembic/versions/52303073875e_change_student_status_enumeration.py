"""change student status enumeration

Revision ID: 52303073875e
Revises: 8c0952812c90
Create Date: 2026-10-19 21:05:15.259613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52303073875e'
down_revision: Union[str, Sequence[str], None] = '8c0952812c90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires ADD VALUE commands outside of a single multi-statement transaction,
    # or simple sequential execution:
    op.execute("ALTER TYPE student_status_name ADD VALUE IF NOT EXISTS 'LEAD_BEFORE'")
    op.execute("ALTER TYPE student_status_name ADD VALUE IF NOT EXISTS 'LEAD_APPOINTED'")
    op.execute("ALTER TYPE student_status_name ADD VALUE IF NOT EXISTS 'LEAD_AFTER'")


def downgrade() -> None:
    # Note: PostgreSQL does NOT support removing values from an ENUM directly.
    # Leaving downgrade empty (pass) is the standard practice for adding enum values.
    pass