"""drop legacy lesson date and duration

Revision ID: 0372e374114f
Revises: 5adf1fc672e3
Create Date: 2026-11-25 13:59:36.968941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0372e374114f'
down_revision: Union[str, Sequence[str], None] = '5adf1fc672e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("lesson", "date")
    op.drop_column("lesson", "duration_minutes")


def downgrade() -> None:
    op.add_column("lesson", sa.Column("date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lesson", sa.Column("duration_minutes", sa.Integer(), nullable=True))