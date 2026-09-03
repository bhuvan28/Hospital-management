from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.finance import DonationCategory
from app.models.lookup import State, WardClinic
from app.models.user import User
from app.schemas.common import LookupCreate, LookupOut, LookupUpdate

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


def _list(db: Session, model) -> list:
    return list(db.scalars(select(model).order_by(model.name)).all())


@router.get("/wards", response_model=list[LookupOut])
def list_wards(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _list(db, WardClinic)


@router.get("/states", response_model=list[LookupOut])
def list_states(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _list(db, State)


@router.get("/donation-categories", response_model=list[LookupOut])
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _list(db, DonationCategory)


def _create(db: Session, model, payload: LookupCreate):
    if db.scalar(select(model).where(model.name == payload.name.strip())):
        raise ConflictError("Name must be unique")
    row = model(name=payload.name.strip(), active=payload.active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _update(db: Session, model, item_id: int, payload: LookupUpdate):
    row = db.get(model, item_id)
    if row is None:
        raise NotFoundError("Record not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = data["name"].strip()
        clash = db.scalar(select(model).where(model.name == data["name"], model.id != row.id))
        if clash:
            raise ConflictError("Name must be unique")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/wards", response_model=LookupOut, status_code=201)
def create_ward(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _create(db, WardClinic, payload)


@router.patch("/wards/{item_id}", response_model=LookupOut)
def update_ward(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _update(db, WardClinic, item_id, payload)


@router.post("/states", response_model=LookupOut, status_code=201)
def create_state(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _create(db, State, payload)


@router.patch("/states/{item_id}", response_model=LookupOut)
def update_state(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _update(db, State, item_id, payload)


@router.post("/donation-categories", response_model=LookupOut, status_code=201)
def create_category(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _create(db, DonationCategory, payload)


@router.patch("/donation-categories/{item_id}", response_model=LookupOut)
def update_category(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    _: User = require_permission("settings:manage"),
):
    return _update(db, DonationCategory, item_id, payload)
