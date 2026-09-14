from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
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
    MealUpdate,
    PettyCashCreate,
    PettyCashOut,
    PettyCashSummary,
    PettyCashUpdate,
)
from app.services.audit import write_audit
from app.services.finance import donation_totals, meal_totals, petty_totals

donations_router = APIRouter(prefix="/api/donations", tags=["donations"])
petty_router = APIRouter(prefix="/api/petty-cash", tags=["petty-cash"])
meals_router = APIRouter(prefix="/api/meal-sponsorships", tags=["meal-sponsorships"])


def _donation_snapshot(row: Donation) -> dict:
    return {
        "date": row.date.isoformat(),
        "donor_name": row.donor_name,
        "type": row.type.value,
        "category_id": row.category_id,
        "category_tag": row.category_tag,
        "item_remark": row.item_remark,
        "quantity": row.quantity,
        "amount": str(row.amount),
    }


def _petty_snapshot(row: PettyCashEntry) -> dict:
    groceries = row.groceries_sponsored
    return {
        "month": row.month.isoformat(),
        "budgeted": str(row.budgeted),
        "actual": str(row.actual),
        "groceries_sponsored": str(groceries) if groceries is not None else None,
        "category": row.category.value,
        "remarks": row.remarks,
    }


def _meal_snapshot(row: MealSponsorship) -> dict:
    return {
        "date": row.date.isoformat(),
        "sponsor_name": row.sponsor_name,
        "item_remark": row.item_remark,
        "meal_type": row.meal_type.value,
        "pax": row.pax,
        "amount": str(row.amount),
    }


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
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Donation.donor_name.ilike(like), Donation.item_remark.ilike(like)))
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
    return donation_totals(db, year=year, month=month)


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
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        if db.get(DonationCategory, data["category_id"]) is None:
            raise NotFoundError("Donation category not found")
    before = _donation_snapshot(row)
    for key, value in data.items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="Donation",
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after=_donation_snapshot(row),
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
        before=_donation_snapshot(row),
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
    return petty_totals(db, year=year, month=month)


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
    before = _petty_snapshot(row)
    data = payload.model_dump(exclude_unset=True)
    if "month" in data and data["month"]:
        data["month"] = data["month"].replace(day=1)
    next_month = data.get("month", row.month)
    next_category = data.get("category", row.category)
    clash = db.scalar(
        select(PettyCashEntry).where(
            PettyCashEntry.month == next_month,
            PettyCashEntry.category == next_category,
            PettyCashEntry.id != row.id,
        )
    )
    if clash:
        raise ConflictError("A petty cash entry already exists for this month and category")
    for key, value in data.items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="PettyCashEntry",
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after=_petty_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _petty_out(row)


@petty_router.delete("/{entry_id}", status_code=204)
def delete_petty(
    entry_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("petty_cash:write"),
):
    row = db.get(PettyCashEntry, entry_id)
    if row is None:
        raise NotFoundError("Petty cash entry not found")
    write_audit(
        db,
        user_id=actor.id,
        entity="PettyCashEntry",
        entity_id=row.id,
        action=AuditAction.DELETE,
        before={
            "month": row.month.isoformat(),
            "category": row.category.value,
            "budgeted": str(row.budgeted),
            "actual": str(row.actual),
        },
    )
    db.delete(row)
    db.commit()


@meals_router.get("", response_model=Page[MealOut])
def list_meals(
    q: str | None = None,
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
    if q:
        stmt = stmt.where(MealSponsorship.sponsor_name.ilike(f"%{q}%"))
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
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("meals:read"),
):
    return meal_totals(db, year=year, month=month, start=start, end=end)


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


@meals_router.patch("/{meal_id}", response_model=MealOut)
def update_meal(
    meal_id: int,
    payload: MealUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("meals:write"),
):
    row = db.get(MealSponsorship, meal_id)
    if row is None:
        raise NotFoundError("Meal sponsorship not found")
    before = _meal_snapshot(row)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="MealSponsorship",
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after=_meal_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return MealOut.model_validate(row)


@meals_router.delete("/{meal_id}", status_code=204)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("meals:write"),
):
    row = db.get(MealSponsorship, meal_id)
    if row is None:
        raise NotFoundError("Meal sponsorship not found")
    write_audit(
        db,
        user_id=actor.id,
        entity="MealSponsorship",
        entity_id=row.id,
        action=AuditAction.DELETE,
        before={"sponsor_name": row.sponsor_name, "amount": str(row.amount), "date": row.date.isoformat()},
    )
    db.delete(row)
    db.commit()
