from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import User
from app.security.rbac import has_permission
from app.services import occupancy as occupancy_service
from app.services.finance import aggregated_finance_snapshot

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload: dict = {"role": user.role.value, "generated_on": date.today().isoformat()}
    occupancy = occupancy_service.get_occupancy_summary(db)
    if has_permission(user.role, "dashboard:ops") or has_permission(user.role, "rooms:read"):
        payload["occupancy"] = occupancy
        payload["patient_census"] = db.scalar(select(func.count(Patient.id))) or 0
        payload["in_house_census"] = occupancy["occupied_rooms"]
        payload["current_occupants"] = occupancy_service.current_occupants_summary(db)
        payload["todays_movements"] = occupancy_service.todays_movements(db)
        if has_permission(user.role, "waitlist:read"):
            payload["open_waitlist"] = occupancy_service.open_waitlist_summary(db)
    if has_permission(user.role, "dashboard:finance") or (
        user.role == UserRole.VIEWER and has_permission(user.role, "reports:finance")
    ):
        payload.update(aggregated_finance_snapshot(db))
    if has_permission(user.role, "dashboard:viewer") and user.role == UserRole.VIEWER:
        payload["occupancy"] = occupancy
        # Current in-house count only — never the lifetime registry (that is not a census).
        payload["patient_census"] = occupancy["occupied_rooms"]
        payload["in_house_census"] = occupancy["occupied_rooms"]
        payload.pop("current_occupants", None)
        payload.pop("todays_movements", None)
        payload.pop("open_waitlist", None)
        payload["note"] = "Viewer dashboard shows aggregated figures only. Patient identifiers are not included."
    if not payload.get("occupancy") and not payload.get("donations"):
        payload["message"] = "No dashboard widgets are assigned to this role."
    return payload
