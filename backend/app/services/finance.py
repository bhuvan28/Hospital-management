from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.finance import Donation, MealSponsorship, PettyCashEntry
from app.schemas.finance import DonationSummary, MealSummary, PettyCashSummary


def donation_totals(db: Session, *, year: int | None = None, month: int | None = None) -> DonationSummary:
    today = date.today()
    year = year or today.year
    rows = list(
        db.scalars(
            select(Donation)
            .options(joinedload(Donation.category))
            .where(
                Donation.date >= date(year, 1, 1),
                Donation.date <= date(year, 12, 31),
            )
        )
        .unique()
        .all()
    )
    annual = sum((Decimal(r.amount) for r in rows), Decimal("0"))
    month_no = month or today.month
    monthly = sum((Decimal(r.amount) for r in rows if r.date.month == month_no), Decimal("0"))
    by_type: dict[str, Decimal] = {}
    by_category: dict[str, Decimal] = {}
    monthly_by_type: dict[str, Decimal] = {}
    monthly_by_category: dict[str, Decimal] = {}
    for row in rows:
        amount = Decimal(row.amount)
        by_type[row.type.value] = by_type.get(row.type.value, Decimal("0")) + amount
        label = row.category.name if row.category else (row.category_tag or "Uncategorised")
        by_category[label] = by_category.get(label, Decimal("0")) + amount
        if row.date.month == month_no:
            monthly_by_type[row.type.value] = monthly_by_type.get(row.type.value, Decimal("0")) + amount
            monthly_by_category[label] = monthly_by_category.get(label, Decimal("0")) + amount
    return DonationSummary(
        total_amount=annual,
        total_count=len(rows),
        monthly_total=monthly,
        annual_total=annual,
        by_type=by_type,
        by_category=by_category,
        monthly_by_type=monthly_by_type,
        monthly_by_category=monthly_by_category,
    )


def petty_totals(db: Session, *, year: int | None = None, month: int | None = None) -> PettyCashSummary:
    today = date.today()
    year = year or today.year
    stmt = select(PettyCashEntry).where(
        PettyCashEntry.month >= date(year, 1, 1),
        PettyCashEntry.month <= date(year, 12, 31),
    )
    rows = list(db.scalars(stmt).all())
    if month:
        rows = [row for row in rows if row.month.month == month]
    budgeted = sum((Decimal(row.budgeted) for row in rows), Decimal("0"))
    actual = sum((Decimal(row.actual) for row in rows), Decimal("0"))
    groceries = sum((Decimal(row.groceries_sponsored) for row in rows), Decimal("0"))
    return PettyCashSummary(
        total_budgeted=budgeted,
        total_actual=actual,
        total_balance=budgeted - actual,
        total_groceries_sponsored=groceries,
    )


def meal_totals(
    db: Session,
    *,
    year: int | None = None,
    month: int | None = None,
    start: date | None = None,
    end: date | None = None,
) -> MealSummary:
    today = date.today()
    if start and end:
        rows = list(
            db.scalars(
                select(MealSponsorship).where(MealSponsorship.date >= start, MealSponsorship.date <= end)
            ).all()
        )
        monthly = rows
    else:
        year = year or today.year
        month_no = month or today.month
        rows = list(
            db.scalars(
                select(MealSponsorship).where(
                    MealSponsorship.date >= date(year, 1, 1),
                    MealSponsorship.date <= date(year, 12, 31),
                )
            ).all()
        )
        monthly = [row for row in rows if row.date.month == month_no]
    by_type: dict[str, Decimal] = {}
    for row in rows:
        by_type[row.meal_type.value] = by_type.get(row.meal_type.value, Decimal("0")) + Decimal(row.amount)
    return MealSummary(
        total_amount=sum((Decimal(row.amount) for row in rows), Decimal("0")),
        total_pax=sum(row.pax for row in rows),
        monthly_total=sum((Decimal(row.amount) for row in monthly), Decimal("0")),
        by_meal_type=by_type,
    )


def aggregated_finance_snapshot(db: Session) -> dict:
    """Totals only — no donor, sponsor, or other identifying names."""
    donations = donation_totals(db)
    petty = petty_totals(db)
    meals = meal_totals(db)
    return {
        "donations": donations.model_dump(mode="json"),
        "petty_cash": petty.model_dump(mode="json"),
        "meals": meals.model_dump(mode="json"),
    }
