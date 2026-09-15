from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ValidationAppError
from app.models.finance import Donation, MealSponsorship, PettyCashEntry
from app.schemas.finance import DonationSummary, MealSummary, PettyCashSummary


def ensure_date_range(start: date | None, end: date | None) -> None:
    if start and end and start > end:
        raise ValidationAppError("Start date cannot be after the end date")


def donation_statement(
    *,
    q: str | None = None,
    donation_type: str | None = None,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    year: int | None = None,
) -> Select:
    """House-level donation ledger query. Date filters are optional; default is calendar year."""
    ensure_date_range(start, end)
    stmt = select(Donation).options(joinedload(Donation.category))
    if start:
        stmt = stmt.where(Donation.date >= start)
    elif year is not None:
        stmt = stmt.where(Donation.date >= date(year, 1, 1))
    if end:
        stmt = stmt.where(Donation.date <= end)
    elif year is not None:
        stmt = stmt.where(Donation.date <= date(year, 12, 31))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Donation.donor_name.ilike(like), Donation.item_remark.ilike(like)))
    if donation_type:
        stmt = stmt.where(Donation.type == donation_type)
    if category_id:
        stmt = stmt.where(Donation.category_id == category_id)
    return stmt.order_by(Donation.date.desc(), Donation.id.desc())


def meal_statement(
    *,
    q: str | None = None,
    meal_type: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> Select:
    ensure_date_range(start, end)
    stmt = select(MealSponsorship)
    if start:
        stmt = stmt.where(MealSponsorship.date >= start)
    if end:
        stmt = stmt.where(MealSponsorship.date <= end)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(MealSponsorship.sponsor_name.ilike(like), MealSponsorship.item_remark.ilike(like))
        )
    if meal_type:
        stmt = stmt.where(MealSponsorship.meal_type == meal_type)
    return stmt.order_by(MealSponsorship.date.desc(), MealSponsorship.id.desc())


def donation_totals(
    db: Session,
    *,
    year: int | None = None,
    month: int | None = None,
    start: date | None = None,
    end: date | None = None,
    donation_type: str | None = None,
    category_id: int | None = None,
    q: str | None = None,
) -> DonationSummary:
    today = date.today()
    bounded_year = None if start or end else (year or today.year)
    rows = list(
        db.scalars(
            donation_statement(
                q=q,
                donation_type=donation_type,
                category_id=category_id,
                start=start,
                end=end,
                year=bounded_year,
            )
        )
        .unique()
        .all()
    )
    period_total = sum((Decimal(r.amount) for r in rows), Decimal("0"))
    month_no = month or today.month
    if start or end:
        monthly_rows = rows
    else:
        monthly_rows = [r for r in rows if r.date.month == month_no]
    monthly = sum((Decimal(r.amount) for r in monthly_rows), Decimal("0"))
    by_type: dict[str, Decimal] = {}
    by_category: dict[str, Decimal] = {}
    monthly_by_type: dict[str, Decimal] = {}
    monthly_by_category: dict[str, Decimal] = {}
    monthly_ids = {id(row) for row in monthly_rows}
    for row in rows:
        amount = Decimal(row.amount)
        by_type[row.type.value] = by_type.get(row.type.value, Decimal("0")) + amount
        label = row.category.name if row.category else (row.category_tag or "Uncategorised")
        by_category[label] = by_category.get(label, Decimal("0")) + amount
        if id(row) in monthly_ids:
            monthly_by_type[row.type.value] = monthly_by_type.get(row.type.value, Decimal("0")) + amount
            monthly_by_category[label] = monthly_by_category.get(label, Decimal("0")) + amount
    return DonationSummary(
        total_amount=period_total,
        total_count=len(rows),
        monthly_total=monthly,
        annual_total=period_total,
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
    q: str | None = None,
    meal_type: str | None = None,
) -> MealSummary:
    today = date.today()
    if start or end:
        rows = list(db.scalars(meal_statement(q=q, meal_type=meal_type, start=start, end=end)).all())
        monthly = rows
    else:
        year = year or today.year
        month_no = month or today.month
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        rows = list(
            db.scalars(meal_statement(q=q, meal_type=meal_type, start=year_start, end=year_end)).all()
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
