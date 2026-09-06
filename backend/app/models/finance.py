from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DonationType, MealType, PettyCashCategory


class DonationCategory(Base):
    __tablename__ = "donation_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    donations = relationship("Donation", back_populates="category")


class Donation(Base):
    """House-level donation. PRD v1 does not link donations to patients."""

    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    donor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[DonationType] = mapped_column(
        Enum(DonationType, name="donation_type", native_enum=False, length=32),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(ForeignKey("donation_categories.id"))
    category_tag: Mapped[str | None] = mapped_column(String(120))
    item_remark: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category = relationship("DonationCategory", back_populates="donations")


class PettyCashEntry(Base):
    __tablename__ = "petty_cash_entries"
    __table_args__ = (
        UniqueConstraint("month", "category", name="uq_petty_cash_month_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    budgeted: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    actual: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    groceries_sponsored: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    category: Mapped[PettyCashCategory] = mapped_column(
        Enum(PettyCashCategory, name="petty_cash_category", native_enum=False, length=40),
        nullable=False,
    )
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MealSponsorship(Base):
    __tablename__ = "meal_sponsorships"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sponsor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_remark: Mapped[str | None] = mapped_column(Text)
    meal_type: Mapped[MealType] = mapped_column(
        Enum(MealType, name="meal_type", native_enum=False, length=20),
        nullable=False,
    )
    pax: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
