"""Initial RMH HCTM UKM schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "ward_clinics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "donation_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_number", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("room_number", name="uq_rooms_room_number"),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("registration_no", sa.String(64), nullable=False),
        sa.Column("nric", sa.String(32), nullable=False),
        sa.Column("gender", sa.String(20), nullable=False),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("referring_doctor", sa.String(200)),
        sa.Column("ward_clinic_id", sa.Integer(), sa.ForeignKey("ward_clinics.id"), nullable=False),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("registered_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sibling_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sibling_names", sa.Text()),
    )
    op.create_index("ix_patients_name", "patients", ["name"])
    op.create_index("ix_patients_registration_no", "patients", ["registration_no"], unique=True)

    op.create_table(
        "guardians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("relationship", sa.String(80), nullable=False),
        sa.Column("contact", sa.String(80), nullable=False),
    )
    op.create_table(
        "social_worker_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("assessed_fee_amount", sa.Numeric(12, 2)),
        sa.Column("assessed_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("assessed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "room_stays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("hospital_admission_date", sa.Date()),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date()),
        sa.Column("officer_on_duty_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("room_inspected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "uq_room_active_stay",
        "room_stays",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("check_out_date IS NULL"),
        sqlite_where=sa.text("check_out_date IS NULL"),
    )
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("added_date", sa.Date(), nullable=False),
        sa.Column("resolved_date", sa.Date()),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "donations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("donor_name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("donation_categories.id")),
        sa.Column("category_tag", sa.String(120)),
        sa.Column("item_remark", sa.Text()),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_donations_date", "donations", ["date"])
    op.create_table(
        "petty_cash_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("budgeted", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual", sa.Numeric(12, 2), nullable=False),
        sa.Column("groceries_sponsored", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("month", "category", name="uq_petty_cash_month_category"),
    )
    op.create_index("ix_petty_cash_entries_month", "petty_cash_entries", ["month"])
    op.create_table(
        "meal_sponsorships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sponsor_name", sa.String(200), nullable=False),
        sa.Column("item_remark", sa.Text()),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("pax", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_meal_sponsorships_date", "meal_sponsorships", ["date"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("entity", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("before_values", sa.JSON()),
        sa.Column("after_values", sa.JSON()),
        sa.Column("changed_fields", sa.JSON()),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("meal_sponsorships")
    op.drop_table("petty_cash_entries")
    op.drop_table("donations")
    op.drop_table("waitlist_entries")
    op.drop_table("room_stays")
    op.drop_table("social_worker_assessments")
    op.drop_table("guardians")
    op.drop_table("patients")
    op.drop_table("rooms")
    op.drop_table("donation_categories")
    op.drop_table("states")
    op.drop_table("ward_clinics")
    op.drop_table("users")
