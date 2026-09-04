from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.finance import donation_summary, meal_summary, petty_summary
from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.security.rbac import has_permission
from app.services import occupancy as occupancy_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload: dict = {"role": user.role.value, "generated_on": date.today().isoformat()}
    if has_permission(user.role, "dashboard:ops") or has_permission(user.role, "rooms:read"):
        payload["occupancy"] = occupancy_service.get_occupancy_summary(db)
        payload["patient_census"] = db.scalar(select(func.count(Patient.id))) or 0
        payload["current_occupants"] = occupancy_service.current_occupants_summary(db)
        payload["todays_movements"] = occupancy_service.todays_movements(db)
    if has_permission(user.role, "dashboard:finance"):
        payload["donations"] = donation_summary(db=db, year=None, month=None, _=user).model_dump(mode="json")
        payload["petty_cash"] = petty_summary(db=db, year=None, month=None, _=user).model_dump(mode="json")
        payload["meals"] = meal_summary(db=db, year=None, month=None, _=user).model_dump(mode="json")
    if has_permission(user.role, "dashboard:viewer") and user.role.value == "viewer":
        payload["occupancy"] = occupancy_service.get_occupancy_summary(db)
        payload["patient_census"] = db.scalar(select(func.count(Patient.id))) or 0
        payload.pop("current_occupants", None)
        payload.pop("todays_movements", None)
        payload["note"] = "Viewer dashboard shows aggregated figures only. Patient identifiers are not included."
    if not payload.get("occupancy") and not payload.get("donations"):
        payload["message"] = "No dashboard widgets are assigned to this role."
    return payload
