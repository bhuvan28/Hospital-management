from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import AuditAction
from app.models.lookup import State, WardClinic
from app.models.patient import Guardian, Patient, SocialWorkerAssessment
from app.models.room import RoomStay, WaitlistEntry
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit import write_audit


def _patient_options():
    return (
        joinedload(Patient.ward_clinic),
        joinedload(Patient.state),
        joinedload(Patient.guardians),
        joinedload(Patient.assessment),
    )


def get_patient(db: Session, patient_id: int) -> Patient:
    patient = (
        db.execute(select(Patient).options(*_patient_options()).where(Patient.id == patient_id))
        .unique()
        .scalar_one_or_none()
    )
    if patient is None:
        raise NotFoundError("Patient not found")
    return patient


SORTABLE = {
    "name": Patient.name,
    "registration_no": Patient.registration_no,
    "registered_at": Patient.registered_at,
    "status": Patient.status,
}


def patient_query(
    db: Session,
    *,
    q: str | None = None,
    registration_no: str | None = None,
    ward_clinic_id: int | None = None,
    state_id: int | None = None,
    status: str | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
) -> Select:
    stmt = select(Patient).options(*_patient_options())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Patient.name.ilike(like), Patient.registration_no.ilike(like)))
    if registration_no:
        stmt = stmt.where(Patient.registration_no.ilike(f"%{registration_no.strip()}%"))
    if ward_clinic_id:
        stmt = stmt.where(Patient.ward_clinic_id == ward_clinic_id)
    if state_id:
        stmt = stmt.where(Patient.state_id == state_id)
    if status:
        stmt = stmt.where(Patient.status == status)
    column = SORTABLE.get(sort_by, Patient.name)
    ordered = column.desc() if sort_dir == "desc" else column.asc()
    return stmt.order_by(ordered, Patient.id)


def paginate_patients(
    db: Session,
    stmt: Select,
    page: int,
    page_size: int,
) -> tuple[list[Patient], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all())
    return items, total


def _ensure_lookups(db: Session, ward_id: int, state_id: int) -> None:
    if db.get(WardClinic, ward_id) is None:
        raise NotFoundError("Ward/Clinic not found")
    if db.get(State, state_id) is None:
        raise NotFoundError("State/region not found")


def _snapshot(patient: Patient) -> dict:
    return {
        "name": patient.name,
        "registration_no": patient.registration_no,
        "nric": patient.nric,
        "gender": patient.gender.value,
        "dob": patient.dob.isoformat(),
        "address": patient.address,
        "diagnosis": patient.diagnosis,
        "referring_doctor": patient.referring_doctor,
        "ward_clinic_id": patient.ward_clinic_id,
        "state_id": patient.state_id,
        "status": patient.status.value,
        "registered_online": patient.registered_online,
        "sibling_count": patient.sibling_count,
        "sibling_names": patient.sibling_names,
    }


def create_patient(db: Session, data: PatientCreate, actor: User) -> Patient:
    _ensure_lookups(db, data.ward_clinic_id, data.state_id)
    exists = db.scalar(select(Patient).where(Patient.registration_no == data.registration_no.strip()))
    if exists:
        raise ConflictError("A patient with this registration number already exists")

    now = datetime.now(timezone.utc)
    patient = Patient(
        name=data.name.strip(),
        registration_no=data.registration_no.strip(),
        nric=data.nric.strip(),
        gender=data.gender,
        dob=data.dob,
        address=data.address.strip(),
        diagnosis=data.diagnosis.strip(),
        referring_doctor=data.referring_doctor,
        ward_clinic_id=data.ward_clinic_id,
        state_id=data.state_id,
        status=data.status,
        registered_online=data.registered_online,
        registered_at=data.registered_at or now,
        sibling_count=data.sibling_count,
        sibling_names=data.sibling_names,
        guardians=[
            Guardian(name=g.name.strip(), relationship=g.relationship.strip(), contact=g.contact.strip())
            for g in data.guardians
        ],
    )
    if data.assessment:
        patient.assessment = SocialWorkerAssessment(
            payload=data.assessment.payload or {},
            notes=data.assessment.notes,
            assessed_fee_amount=data.assessment.assessed_fee_amount,
            assessed_by_id=actor.id,
            assessed_at=now,
        )
    db.add(patient)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="Patient",
        entity_id=patient.id,
        action=AuditAction.CREATE,
        after=_snapshot(patient),
    )
    db.commit()
    return get_patient(db, patient.id)


def update_patient(db: Session, patient_id: int, data: PatientUpdate, actor: User) -> Patient:
    patient = get_patient(db, patient_id)
    before = _snapshot(patient)
    payload = data.model_dump(exclude_unset=True)
    if "registration_no" in payload and payload["registration_no"]:
        payload["registration_no"] = payload["registration_no"].strip()
        clash = db.scalar(
            select(Patient).where(
                Patient.registration_no == payload["registration_no"],
                Patient.id != patient.id,
            )
        )
        if clash:
            raise ConflictError("A patient with this registration number already exists")
    if "ward_clinic_id" in payload or "state_id" in payload:
        _ensure_lookups(
            db,
            payload.get("ward_clinic_id", patient.ward_clinic_id),
            payload.get("state_id", patient.state_id),
        )

    guardians_in = payload.pop("guardians", None)
    assessment_in = payload.pop("assessment", None)
    for key, value in payload.items():
        setattr(patient, key, value)

    if guardians_in is not None:
        patient.guardians.clear()
        db.flush()
        for g in data.guardians or []:
            patient.guardians.append(
                Guardian(name=g.name.strip(), relationship=g.relationship.strip(), contact=g.contact.strip())
            )

    if assessment_in is not None and data.assessment is not None:
        now = datetime.now(timezone.utc)
        if patient.assessment is None:
            patient.assessment = SocialWorkerAssessment(
                payload=data.assessment.payload or {},
                notes=data.assessment.notes,
                assessed_fee_amount=data.assessment.assessed_fee_amount,
                assessed_by_id=actor.id,
                assessed_at=now,
            )
        else:
            # Keep confirmed JSON when an edit omits or sends an empty payload.
            if data.assessment.payload:
                patient.assessment.payload = data.assessment.payload
            patient.assessment.notes = data.assessment.notes
            patient.assessment.assessed_fee_amount = data.assessment.assessed_fee_amount
            patient.assessment.assessed_by_id = actor.id
            patient.assessment.assessed_at = now

    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="Patient",
        entity_id=patient.id,
        action=AuditAction.UPDATE,
        before=before,
        after=_snapshot(patient),
    )
    db.commit()
    return get_patient(db, patient.id)


def delete_patient(db: Session, patient_id: int, actor: User) -> None:
    patient = get_patient(db, patient_id)
    if db.scalar(select(RoomStay.id).where(RoomStay.patient_id == patient_id).limit(1)):
        raise ConflictError("Cannot delete a patient who has room-stay history.")
    if db.scalar(select(WaitlistEntry.id).where(WaitlistEntry.patient_id == patient_id).limit(1)):
        raise ConflictError("Cannot delete a patient who has waiting-list history.")
    before = _snapshot(patient)
    write_audit(
        db,
        user_id=actor.id,
        entity="Patient",
        entity_id=patient.id,
        action=AuditAction.DELETE,
        before=before,
    )
    db.delete(patient)
    db.commit()
