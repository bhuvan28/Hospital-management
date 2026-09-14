from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction
from app.models.patient import Patient
from app.models.room import RoomStay, WaitlistEntry
from app.models.user import User
from app.schemas.room import WaitlistCreate, WaitlistOut, WaitlistResolve
from app.services.audit import write_audit
from app.services.exports import to_excel_table
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
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("waitlist:read"),
):
    stmt = select(WaitlistEntry).options(joinedload(WaitlistEntry.patient)).order_by(WaitlistEntry.added_date)
    if not include_resolved:
        stmt = stmt.where(WaitlistEntry.resolved_date.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.join(WaitlistEntry.patient).where(
            or_(Patient.name.ilike(like), Patient.registration_no.ilike(like))
        )
    return [_out(entry) for entry in db.scalars(stmt).unique().all()]


@router.get("/export")
def export_waitlist(
    include_resolved: bool = False,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("waitlist:read"),
):
    rows = list_waitlist(include_resolved=include_resolved, q=q, db=db, _=_)
    content = to_excel_table(
        "Waiting List",
        f"Days waited are calculated from added and resolved dates · {date.today().isoformat()}",
        ["Patient", "Registration", "Added", "Days Waited", "Resolved", "Remarks"],
        [
            [
                row.patient_name,
                row.registration_no,
                row.added_date.isoformat(),
                row.days_waited,
                row.resolved_date.isoformat() if row.resolved_date else "Open",
                row.remarks or "",
            ]
            for row in rows
        ],
        summary=[("open_entries", sum(1 for row in rows if row.resolved_date is None))],
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="RMH-HCTM-UKM-waitlist.xlsx"'},
    )


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
    active_stay = db.scalar(
        select(RoomStay).where(RoomStay.patient_id == payload.patient_id, RoomStay.check_out_date.is_(None))
    )
    if active_stay is not None:
        raise ConflictError("Patient already occupies a room and cannot be added to the waiting list")
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
        after={
            "patient_id": entry.patient_id,
            "added_date": entry.added_date.isoformat(),
            "remarks": entry.remarks,
        },
    )
    db.commit()
    db.refresh(entry)
    entry.patient = patient
    return _out(entry)


@router.post("/{entry_id}/resolve", response_model=WaitlistOut)
def resolve_waitlist(
    entry_id: int,
    payload: WaitlistResolve | None = None,
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
    resolved = (payload.resolved_date if payload and payload.resolved_date else date.today())
    if resolved < entry.added_date:
        raise ConflictError("Resolved date cannot be before the date the family was added")
    before = {"resolved_date": None, "remarks": entry.remarks}
    entry.resolved_date = resolved
    if payload and payload.remarks is not None:
        entry.remarks = payload.remarks
    write_audit(
        db,
        user_id=actor.id,
        entity="WaitlistEntry",
        entity_id=entry.id,
        action=AuditAction.RESOLVE,
        before=before,
        after={"resolved_date": entry.resolved_date.isoformat(), "remarks": entry.remarks},
    )
    db.commit()
    db.refresh(entry)
    return _out(entry)
