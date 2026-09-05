from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction
from app.models.finance import Donation, DonationCategory, MealSponsorship, PettyCashEntry
from app.models.user import User
from app.schemas.common import Page
from app.schemas.finance import (
    DonationCreate,
    DonationOut,
    DonationSummary,
    DonationUpdate,
    MealCreate,
    MealOut,
    MealSummary,
    PettyCashCreate,
    PettyCashOut,
    PettyCashSummary,
    PettyCashUpdate,
)
from app.services.audit import write_audit

donations_router = APIRouter(prefix="/api/donations", tags=["donations"])
petty_router = APIRouter(prefix="/api/petty-cash", tags=["petty-cash"])
meals_router = APIRouter(prefix="/api/meal-sponsorships", tags=["meal-sponsorships"])


def _donation_out(row: Donation) -> DonationOut:
    return DonationOut(
        id=row.id,
        date=row.date,
        donor_name=row.donor_name,
        type=row.type,
        category_id=row.category_id,
        category_name=row.category.name if row.category else None,
        category_tag=row.category_tag,
        item_remark=row.item_remark,
        quantity=row.quantity,
        amount=row.amount,
    )


def _petty_out(row: PettyCashEntry) -> PettyCashOut:
    return PettyCashOut(
        id=row.id,
        month=row.month,
        budgeted=row.budgeted,
        actual=row.actual,
        groceries_sponsored=row.groceries_sponsored,
        category=row.category,
        remarks=row.remarks,
        balance=Decimal(row.budgeted) - Decimal(row.actual),
    )


@donations_router.get("", response_model=Page[DonationOut])
def list_donations(
    q: str | None = None,
    donation_type: str | None = None,
    category_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = require_permission("donations:read"),
):
    stmt = select(Donation).options(joinedload(Donation.category)).order_by(Donation.date.desc())
    if q:
        stmt = stmt.where(Donation.donor_name.ilike(f"%{q}%"))
    if donation_type:
        stmt = stmt.where(Donation.type == donation_type)
    if category_id:
        stmt = stmt.where(Donation.category_id == category_id)
    if start:
        stmt = stmt.where(Donation.date >= start)
    if end:
        stmt = stmt.where(Donation.date <= end)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all())
    pages = (total + page_size - 1) // page_size if total else 0
    return Page(items=[_donation_out(i) for i in items], total=total, page=page, page_size=page_size, pages=pages)


@donations_router.get("/summary", response_model=DonationSummary)
def donation_summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("donations:read"),
):
    today = date.today()
    year = year or today.year
    rows = list(
        db.scalars(
            select(Donation).options(joinedload(Donation.category)).where(
                Donation.date >= date(year, 1, 1),
                Donation.date <= date(year, 12, 31),
            )
        ).unique().all()
    )
    annual = sum((Decimal(r.amount) for r in rows), Decimal("0"))
    month_no = month or today.month
    monthly = sum((Decimal(r.amount) for r in rows if r.date.month == month_no), Decimal("0"))
    by_type: dict[str, Decimal] = {}
    by_category: dict[str, Decimal] = {}
    for r in rows:
        by_type[r.type.value] = by_type.get(r.type.value, Decimal("0")) + Decimal(r.amount)
        label = r.category.name if r.category else (r.category_tag or "Uncategorised")
        by_category[label] = by_category.get(label, Decimal("0")) + Decimal(r.amount)
    return DonationSummary(
        total_amount=annual,
        total_count=len(rows),
        monthly_total=monthly,
        annual_total=annual,
        by_type=by_type,
        by_category=by_category,
    )


@donations_router.post("", response_model=DonationOut, status_code=201)
def create_donation(
    payload: DonationCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("donations:write"),
):
    if payload.category_id and db.get(DonationCategory, payload.category_id) is None:
        raise NotFoundError("Donation category not found")
    row = Donation(**payload.model_dump())
    db.add(row)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="Donation",
        entity_id=row.id,
        action=AuditAction.CREATE,
        after=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(row)
    if row.category_id:
        row.category = db.get(DonationCategory, row.category_id)
    return _donation_out(row)


@donations_router.patch("/{donation_id}", response_model=DonationOut)
def update_donation(
    donation_id: int,
    payload: DonationUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("donations:write"),
):
    row = db.get(Donation, donation_id)
    if row is None:
        raise NotFoundError("Donation not found")
    before = {"donor_name": row.donor_name, "amount": str(row.amount), "type": row.type.value}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="Donation",
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after={"donor_name": row.donor_name, "amount": str(row.amount), "type": row.type.value},
    )
    db.commit()
    db.refresh(row)
    return _donation_out(row)


@donations_router.delete("/{donation_id}", status_code=204)
def delete_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("donations:write"),
):
    row = db.get(Donation, donation_id)
    if row is None:
        raise NotFoundError("Donation not found")
    write_audit(
        db,
        user_id=actor.id,
        entity="Donation",
        entity_id=row.id,
        action=AuditAction.DELETE,
        before={"donor_name": row.donor_name, "amount": str(row.amount)},
    )
    db.delete(row)
    db.commit()


@petty_router.get("", response_model=list[PettyCashOut])
def list_petty(
    year: int | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("petty_cash:read"),
):
    stmt = select(PettyCashEntry).order_by(PettyCashEntry.month.desc(), PettyCashEntry.category)
    if year:
        stmt = stmt.where(PettyCashEntry.month >= date(year, 1, 1), PettyCashEntry.month <= date(year, 12, 31))
    return [_petty_out(row) for row in db.scalars(stmt).all()]


@petty_router.get("/summary", response_model=PettyCashSummary)
def petty_summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("petty_cash:read"),
):
    today = date.today()
    year = year or today.year
    stmt = select(PettyCashEntry).where(
        PettyCashEntry.month >= date(year, 1, 1),
        PettyCashEntry.month <= date(year, 12, 31),
    )
    rows = list(db.scalars(stmt).all())
    if month:
        rows = [r for r in rows if r.month.month == month]
    budgeted = sum((Decimal(r.budgeted) for r in rows), Decimal("0"))
    actual = sum((Decimal(r.actual) for r in rows), Decimal("0"))
    groceries = sum((Decimal(r.groceries_sponsored) for r in rows), Decimal("0"))
    return PettyCashSummary(
        total_budgeted=budgeted,
        total_actual=actual,
        total_balance=budgeted - actual,
        total_groceries_sponsored=groceries,
    )


@petty_router.post("", response_model=PettyCashOut, status_code=201)
def create_petty(
    payload: PettyCashCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("petty_cash:write"),
):
    month = payload.month.replace(day=1)
    clash = db.scalar(
        select(PettyCashEntry).where(PettyCashEntry.month == month, PettyCashEntry.category == payload.category)
    )
    if clash:
        raise ConflictError("A petty cash entry already exists for this month and category")
    row = PettyCashEntry(**{**payload.model_dump(), "month": month})
    db.add(row)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="PettyCashEntry",
        entity_id=row.id,
        action=AuditAction.CREATE,
        after=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(row)
    return _petty_out(row)


@petty_router.patch("/{entry_id}", response_model=PettyCashOut)
def update_petty(
    entry_id: int,
    payload: PettyCashUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("petty_cash:write"),
):
    row = db.get(PettyCashEntry, entry_id)
    if row is None:
        raise NotFoundError("Petty cash entry not found")
    before = {"budgeted": str(row.budgeted), "actual": str(row.actual)}
    data = payload.model_dump(exclude_unset=True)
    if "month" in data and data["month"]:
        data["month"] = data["month"].replace(day=1)
    for key, value in data.items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="PettyCashEntry",
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after={"budgeted": str(row.budgeted), "actual": str(row.actual)},
    )
    db.commit()
    db.refresh(row)
    return _petty_out(row)


@meals_router.get("", response_model=Page[MealOut])
def list_meals(
    start: date | None = None,
    end: date | None = None,
    meal_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = require_permission("meals:read"),
):
    stmt = select(MealSponsorship).order_by(MealSponsorship.date.desc())
    if start:
        stmt = stmt.where(MealSponsorship.date >= start)
    if end:
        stmt = stmt.where(MealSponsorship.date <= end)
    if meal_type:
        stmt = stmt.where(MealSponsorship.meal_type == meal_type)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    pages = (total + page_size - 1) // page_size if total else 0
    return Page(
        items=[MealOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@meals_router.get("/summary", response_model=MealSummary)
def meal_summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("meals:read"),
):
    today = date.today()
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
    monthly = [r for r in rows if r.date.month == month_no]
    by_type: dict[str, Decimal] = {}
    for r in rows:
        by_type[r.meal_type.value] = by_type.get(r.meal_type.value, Decimal("0")) + Decimal(r.amount)
    return MealSummary(
        total_amount=sum((Decimal(r.amount) for r in rows), Decimal("0")),
        total_pax=sum(r.pax for r in rows),
        monthly_total=sum((Decimal(r.amount) for r in monthly), Decimal("0")),
        by_meal_type=by_type,
    )


@meals_router.post("", response_model=MealOut, status_code=201)
def create_meal(
    payload: MealCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("meals:write"),
):
    row = MealSponsorship(**payload.model_dump())
    db.add(row)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="MealSponsorship",
        entity_id=row.id,
        action=AuditAction.CREATE,
        after=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(row)
    return MealOut.model_validate(row)
