"""lesson time ranges and overlap constraint

Revision ID: 5adf1fc672e3
Revises: 14bd5cd64530
Create Date: 2026-11-25 13:30:36.487296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5adf1fc672e3'
down_revision: Union[str, Sequence[str], None] = '14bd5cd64530'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("ALTER TABLE user_account ADD COLUMN IF NOT EXISTS timezone varchar(64) NOT NULL DEFAULT 'UTC'")
    op.execute("ALTER TABLE lesson ADD COLUMN IF NOT EXISTS starts_at timestamptz")
    op.execute("ALTER TABLE lesson ADD COLUMN IF NOT EXISTS ends_at timestamptz")
    op.execute("""
        UPDATE lesson
        SET starts_at = date,
            ends_at = date + duration_minutes * interval '1 minute'
        WHERE starts_at IS NULL OR ends_at IS NULL
    """)
    op.execute("ALTER TABLE lesson ALTER COLUMN starts_at SET NOT NULL")
    op.execute("ALTER TABLE lesson ALTER COLUMN ends_at SET NOT NULL")
    op.execute("""
        ALTER TABLE lesson ADD COLUMN IF NOT EXISTS during tstzrange
        GENERATED ALWAYS AS (tstzrange(starts_at, ends_at, '[)')) STORED
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE lesson ADD CONSTRAINT lesson_end_after_start CHECK (ends_at > starts_at);
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE lesson ADD CONSTRAINT no_overlapping_lessons
            EXCLUDE USING gist (tutor_id WITH =, during WITH &&)
            WHERE (status <> 'CANCELED');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)

def downgrade() -> None:
    """Downgrade schema."""
    pass
