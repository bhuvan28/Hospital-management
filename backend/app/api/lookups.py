from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_any_permission, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction
from app.models.finance import DonationCategory
from app.models.lookup import State, WardClinic
from app.models.user import User
from app.schemas.common import LookupCreate, LookupOut, LookupUpdate
from app.services.audit import write_audit

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
def list_categories(
    db: Session = Depends(get_db),
    _: User = require_any_permission("donations:read", "settings:manage"),
):
    return _list(db, DonationCategory)


def _create(db: Session, model, payload: LookupCreate, actor: User):
    if db.scalar(select(model).where(model.name == payload.name.strip())):
        raise ConflictError("Name must be unique")
    row = model(name=payload.name.strip(), active=payload.active)
    db.add(row)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity=model.__name__,
        entity_id=row.id,
        action=AuditAction.CREATE,
        after={"name": row.name, "active": row.active},
    )
    db.commit()
    db.refresh(row)
    return row


def _update(db: Session, model, item_id: int, payload: LookupUpdate, actor: User):
    row = db.get(model, item_id)
    if row is None:
        raise NotFoundError("Record not found")
    before = {"name": row.name, "active": row.active}
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = data["name"].strip()
        clash = db.scalar(select(model).where(model.name == data["name"], model.id != row.id))
        if clash:
            raise ConflictError("Name must be unique")
    for key, value in data.items():
        setattr(row, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity=model.__name__,
        entity_id=row.id,
        action=AuditAction.UPDATE,
        before=before,
        after={"name": row.name, "active": row.active},
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/wards", response_model=LookupOut, status_code=201)
def create_ward(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _create(db, WardClinic, payload, actor)


@router.patch("/wards/{item_id}", response_model=LookupOut)
def update_ward(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _update(db, WardClinic, item_id, payload, actor)


@router.post("/states", response_model=LookupOut, status_code=201)
def create_state(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _create(db, State, payload, actor)


@router.patch("/states/{item_id}", response_model=LookupOut)
def update_state(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _update(db, State, item_id, payload, actor)


@router.post("/donation-categories", response_model=LookupOut, status_code=201)
def create_category(
    payload: LookupCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _create(db, DonationCategory, payload, actor)


@router.patch("/donation-categories/{item_id}", response_model=LookupOut)
def update_category(
    item_id: int,
    payload: LookupUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    return _update(db, DonationCategory, item_id, payload, actor)
