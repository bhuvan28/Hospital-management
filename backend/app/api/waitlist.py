from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction
from app.models.patient import Patient
from app.models.room import WaitlistEntry
from app.models.user import User
from app.schemas.room import WaitlistCreate, WaitlistOut
from app.services.audit import write_audit
from app.services.occupancy import days_waited

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


def _out(entry: WaitlistEntry) -> WaitlistOut:
    return WaitlistOut(
        id=entry.id,
        patient_id=entry.patient_id,
        patient_name=entry.patient.name if entry.patient else "",
        registration_no=entry.patient.registration_no if entry.patient else "",
        added_date=entry.added_date,
        resolved_date=entry.resolved_date,
        days_waited=days_waited(entry),
        remarks=entry.remarks,
    )


@router.get("", response_model=list[WaitlistOut])
def list_waitlist(
    include_resolved: bool = False,
    db: Session = Depends(get_db),
    _: User = require_permission("waitlist:read"),
):
    stmt = select(WaitlistEntry).options(joinedload(WaitlistEntry.patient)).order_by(WaitlistEntry.added_date)
    if not include_resolved:
        stmt = stmt.where(WaitlistEntry.resolved_date.is_(None))
    return [_out(entry) for entry in db.scalars(stmt).unique().all()]


@router.post("", response_model=WaitlistOut, status_code=201)
def add_waitlist(
    payload: WaitlistCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("waitlist:write"),
):
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise NotFoundError("Patient not found")
    open_entry = db.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.patient_id == payload.patient_id,
            WaitlistEntry.resolved_date.is_(None),
        )
    )
    if open_entry:
        raise ConflictError("Patient is already on the waiting list")
    entry = WaitlistEntry(
        patient_id=payload.patient_id,
        added_date=payload.added_date or date.today(),
        remarks=payload.remarks,
    )
    db.add(entry)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="WaitlistEntry",
        entity_id=entry.id,
        action=AuditAction.CREATE,
        after={"patient_id": entry.patient_id, "added_date": entry.added_date.isoformat()},
    )
    db.commit()
    db.refresh(entry)
    entry.patient = patient
    return _out(entry)


@router.post("/{entry_id}/resolve", response_model=WaitlistOut)
def resolve_waitlist(
    entry_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("waitlist:write"),
):
    entry = db.execute(
        select(WaitlistEntry).options(joinedload(WaitlistEntry.patient)).where(WaitlistEntry.id == entry_id)
    ).unique().scalar_one_or_none()
    if entry is None:
        raise NotFoundError("Waiting list entry not found")
    if entry.resolved_date:
        raise ConflictError("Entry is already resolved")
    entry.resolved_date = date.today()
    write_audit(
        db,
        user_id=actor.id,
        entity="WaitlistEntry",
        entity_id=entry.id,
        action=AuditAction.RESOLVE,
        after={"resolved_date": entry.resolved_date.isoformat()},
    )
    db.commit()
    db.refresh(entry)
    return _out(entry)
