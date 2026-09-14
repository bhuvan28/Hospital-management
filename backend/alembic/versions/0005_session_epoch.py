"""Invalidate sessions after password change

Revision ID: 0005_session_epoch
Revises: 0004_audit_immutable
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_session_epoch"
down_revision: Union[str, Sequence[str], None] = "0004_audit_immutable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_epoch", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "session_epoch")
