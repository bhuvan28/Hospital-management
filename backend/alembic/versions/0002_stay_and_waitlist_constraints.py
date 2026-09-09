"""Stay checkout constraint and unique open waitlist

Revision ID: 0002_constraints
Revises: 0001_initial
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_constraints"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("room_stays") as batch_op:
            batch_op.create_check_constraint(
                "ck_stay_checkout_after_checkin",
                "check_out_date IS NULL OR check_out_date >= check_in_date",
            )
    else:
        op.create_check_constraint(
            "ck_stay_checkout_after_checkin",
            "room_stays",
            "check_out_date IS NULL OR check_out_date >= check_in_date",
        )
    op.create_index(
        "uq_waitlist_open_patient",
        "waitlist_entries",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("resolved_date IS NULL"),
        sqlite_where=sa.text("resolved_date IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("room_stays") as batch_op:
            batch_op.drop_constraint("ck_stay_checkout_after_checkin", type_="check")
    else:
        op.drop_constraint("ck_stay_checkout_after_checkin", "room_stays", type_="check")
    op.drop_index("uq_waitlist_open_patient", table_name="waitlist_entries")
