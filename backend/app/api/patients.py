from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.patient import PatientCreate, PatientDetailOut, PatientListOut, PatientUpdate
from app.security.rbac import has_permission
from app.services import patients as patient_service

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _mask_list(patient, include_sensitive: bool) -> PatientListOut:
    return PatientListOut(
        id=patient.id,
        name=patient.name,
        registration_no=patient.registration_no,
        gender=patient.gender,
        status=patient.status,
        ward_clinic=patient.ward_clinic,
        state=patient.state,
        registered_at=patient.registered_at,
        registered_online=patient.registered_online,
        nric=patient.nric if include_sensitive else None,
        diagnosis=patient.diagnosis if include_sensitive else None,
    )


def _mask_detail(patient, include_sensitive: bool) -> PatientDetailOut:
    base = _mask_list(patient, include_sensitive)
    return PatientDetailOut(
        **base.model_dump(),
        dob=patient.dob if include_sensitive else None,
        address=patient.address if include_sensitive else None,
        referring_doctor=patient.referring_doctor if include_sensitive else None,
        sibling_count=patient.sibling_count,
        sibling_names=patient.sibling_names if include_sensitive else None,
        guardians=patient.guardians if include_sensitive else [],
        assessment=patient.assessment if include_sensitive else None,
    )


@router.get("", response_model=Page[PatientListOut])
def list_patients(
    q: str | None = None,
    registration_no: str | None = None,
    ward_clinic_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = require_permission("patients:read"),
):
    stmt = patient_service.patient_query(
        db, q=q, registration_no=registration_no, ward_clinic_id=ward_clinic_id, status=status
    )
    items, total = patient_service.paginate_patients(db, stmt, page, page_size)
    sensitive = has_permission(actor.role, "patients:read_sensitive")
    pages = (total + page_size - 1) // page_size if total else 0
    return Page(
        items=[_mask_list(p, sensitive) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=PatientDetailOut, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("patients:write"),
):
    patient = patient_service.create_patient(db, payload, actor)
    return _mask_detail(patient, True)


@router.get("/{patient_id}", response_model=PatientDetailOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("patients:read"),
):
    patient = patient_service.get_patient(db, patient_id)
    return _mask_detail(patient, has_permission(actor.role, "patients:read_sensitive"))


@router.patch("/{patient_id}", response_model=PatientDetailOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("patients:write"),
):
    patient = patient_service.update_patient(db, patient_id, payload, actor)
    return _mask_detail(patient, True)


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("patients:delete"),
):
    patient_service.delete_patient(db, patient_id, actor)
