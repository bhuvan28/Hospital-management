"""Audit log immutability and non-negative finance amounts

Revision ID: 0004_audit_immutable
Revises: 0003_patient_stay
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_audit_immutable"
down_revision: Union[str, Sequence[str], None] = "0003_patient_stay"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = {
        "donations": [
            ("ck_donations_amount_nonneg", "amount >= 0"),
            ("ck_donations_quantity_nonneg", "quantity >= 0"),
        ],
        "petty_cash_entries": [
            ("ck_petty_budgeted_nonneg", "budgeted >= 0"),
            ("ck_petty_actual_nonneg", "actual >= 0"),
            ("ck_petty_groceries_nonneg", "groceries_sponsored >= 0"),
        ],
        "meal_sponsorships": [
            ("ck_meals_amount_nonneg", "amount >= 0"),
            ("ck_meals_pax_nonneg", "pax >= 0"),
        ],
    }
    for table, constraints in tables.items():
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(table) as batch_op:
                for name, expr in constraints:
                    batch_op.create_check_constraint(name, expr)
        else:
            for name, expr in constraints:
                op.create_check_constraint(name, table, expr)

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION rmh_prevent_audit_mutation()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                  RAISE EXCEPTION 'audit_logs are immutable';
                END;
                $$;
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE TRIGGER audit_logs_immutable
                BEFORE UPDATE OR DELETE ON audit_logs
                FOR EACH ROW
                EXECUTE FUNCTION rmh_prevent_audit_mutation();
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS rmh_prevent_audit_mutation()"))
    names = [
        ("meal_sponsorships", "ck_meals_pax_nonneg"),
        ("meal_sponsorships", "ck_meals_amount_nonneg"),
        ("petty_cash_entries", "ck_petty_groceries_nonneg"),
        ("petty_cash_entries", "ck_petty_actual_nonneg"),
        ("petty_cash_entries", "ck_petty_budgeted_nonneg"),
        ("donations", "ck_donations_quantity_nonneg"),
        ("donations", "ck_donations_amount_nonneg"),
    ]
    if bind.dialect.name == "sqlite":
        grouped: dict[str, list[str]] = {}
        for table, name in names:
            grouped.setdefault(table, []).append(name)
        for table, constraints in grouped.items():
            with op.batch_alter_table(table) as batch_op:
                for name in constraints:
                    batch_op.drop_constraint(name, type_="check")
    else:
        for table, name in names:
            op.drop_constraint(name, table, type_="check")
