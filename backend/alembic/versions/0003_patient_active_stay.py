"""Unique active stay per patient

Revision ID: 0003_patient_stay
Revises: 0002_constraints
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_patient_stay"
down_revision: Union[str, Sequence[str], None] = "0002_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_patient_active_stay",
        "room_stays",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("check_out_date IS NULL"),
        sqlite_where=sa.text("check_out_date IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_patient_active_stay", table_name="room_stays")
