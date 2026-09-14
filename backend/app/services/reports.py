from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import PatientStatus
from app.models.finance import Donation, PettyCashEntry
from app.models.lookup import State, WardClinic
from app.models.patient import Guardian, Patient, SocialWorkerAssessment
from app.models.room import RoomStay
from app.services.occupancy import daily_occupancy_series


def _stay_in_range(start: date, end: date):
    return and_(
        RoomStay.check_in_date <= end,
        or_(RoomStay.check_out_date.is_(None), RoomStay.check_out_date >= start),
    )


def occupancy_report(db: Session, start: date, end: date) -> dict:
    series = daily_occupancy_series(db, start, end)
    avg = round(sum(row["occupancy_rate"] for row in series) / len(series), 2) if series else 0.0
    return {"start": start.isoformat(), "end": end.isoformat(), "average_occupancy_rate": avg, "days": series}


def occupancy_trend(db: Session, start: date, end: date, grain: str = "month") -> dict:
    series = daily_occupancy_series(db, start, end)
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in series:
        key = row["date"][:7] if grain == "month" else row["date"][:4]
        buckets[key].append(row["occupancy_rate"])
    trend = [{"period": period, "occupancy_rate": round(sum(vals) / len(vals), 2)} for period, vals in buckets.items()]
    return {"grain": grain, "start": start.isoformat(), "end": end.isoformat(), "trend": trend}


def _census_stays(db: Session, start: date, end: date) -> list[RoomStay]:
    return list(db.scalars(select(RoomStay).where(_stay_in_range(start, end))).all())


def _apply_patient_filters(
    patients: list[Patient],
    *,
    ward_clinic_id: int | None = None,
    gender: str | None = None,
    state_id: int | None = None,
    status: str | None = None,
) -> list[Patient]:
    result = patients
    if ward_clinic_id is not None:
        result = [p for p in result if p.ward_clinic_id == ward_clinic_id]
    if gender:
        result = [p for p in result if p.gender.value == gender]
    if state_id is not None:
        result = [p for p in result if p.state_id == state_id]
    if status:
        result = [p for p in result if p.status.value == status]
    return result


def _census_patients(db: Session, start: date, end: date, **filters) -> tuple[list[RoomStay], list[Patient]]:
    stays = _census_stays(db, start, end)
    patient_ids = {stay.patient_id for stay in stays}
    patients = list(db.scalars(select(Patient).where(Patient.id.in_(patient_ids))).all()) if patient_ids else []
    patients = _apply_patient_filters(
        patients, **{k: v for k, v in filters.items() if k in {"ward_clinic_id", "gender", "state_id", "status"}}
    )
    allowed = {p.id for p in patients}
    stays = [stay for stay in stays if stay.patient_id in allowed]
    return stays, patients


def census_report(db: Session, start: date, end: date, **filters) -> dict:
    stays, patients = _census_patients(db, start, end, **filters)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "patient_count": len(patients),
        "stay_count": len(stays),
        "new_count": sum(1 for p in patients if p.status == PatientStatus.NEW),
        "returning_count": sum(1 for p in patients if p.status == PatientStatus.RETURNING),
    }


def census_by_gender(db: Session, start: date, end: date, **filters) -> dict:
    _, patients = _census_patients(db, start, end, **filters)
    counts: dict[str, int] = defaultdict(int)
    for patient in patients:
        counts[patient.gender.value] += 1
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "groups": [{"gender": name, "count": count} for name, count in counts.items()],
    }


def census_by_ward(db: Session, start: date, end: date, **filters) -> dict:
    _, patients = _census_patients(db, start, end, **filters)
    counts: dict[str, int] = defaultdict(int)
    names = {row.id: row.name for row in db.scalars(select(WardClinic)).all()}
    for patient in patients:
        counts[names.get(patient.ward_clinic_id, "Unspecified")] += 1
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "groups": [{"ward": name, "count": count} for name, count in counts.items()],
    }


def census_by_state(db: Session, start: date, end: date, **filters) -> dict:
    _, patients = _census_patients(db, start, end, **filters)
    counts: dict[str, int] = defaultdict(int)
    names = {row.id: row.name for row in db.scalars(select(State)).all()}
    for patient in patients:
        counts[names.get(patient.state_id, "Unspecified")] += 1
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "groups": [{"state": name, "count": count} for name, count in counts.items()],
    }


def new_vs_returning(db: Session, start: date, end: date, **filters) -> dict:
    return census_report(db, start, end, **filters)


def guardian_sibling_totals(db: Session, start: date, end: date, **filters) -> dict:
    _, patients = _census_patients(db, start, end, **filters)
    ids = {p.id for p in patients}
    if not ids:
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "guardian_total": 0,
            "sibling_total": 0,
            "family_count": 0,
        }
    guardian_total = db.scalar(select(func.count(Guardian.id)).where(Guardian.patient_id.in_(ids))) or 0
    sibling_total = db.scalar(select(func.coalesce(func.sum(Patient.sibling_count), 0)).where(Patient.id.in_(ids))) or 0
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "guardian_total": int(guardian_total),
        "sibling_total": int(sibling_total),
        "family_count": len(ids),
    }


def _los_bucket(days: int) -> str:
    if days <= 3:
        return "1-3 days"
    if days <= 7:
        return "4-7 days"
    if days <= 14:
        return "8-14 days"
    if days <= 30:
        return "15-30 days"
    return "31+ days"


def length_of_stay(db: Session, start: date, end: date) -> dict:
    """Bucket nights stayed. Open stays are measured to the report end date.

    No fee or occupancy formula is invented — this is check-out (or report end)
    minus check-in, grouped into the same operational ranges used on the report.
    """
    stays = list(
        db.scalars(
            select(RoomStay).where(
                RoomStay.check_in_date <= end,
                or_(RoomStay.check_out_date.is_(None), RoomStay.check_out_date >= start),
            )
        ).all()
    )
    buckets = defaultdict(int)
    open_count = 0
    completed_count = 0
    for stay in stays:
        end_date = stay.check_out_date or end
        if stay.check_out_date is None:
            open_count += 1
        else:
            completed_count += 1
        days = max((end_date - stay.check_in_date).days, 1)
        buckets[_los_bucket(days)] += 1
    order = ["1-3 days", "4-7 days", "8-14 days", "15-30 days", "31+ days"]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "stay_count": len(stays),
        "open_stays": open_count,
        "completed_stays": completed_count,
        "groups": [{"bucket": label, "count": buckets[label]} for label in order],
        "note": (
            "Open stays are measured to the report end date. Completed stays use check-out date minus check-in date."
        ),
    }


def room_rental_income(db: Session, start: date, end: date, **filters) -> dict:
    """Sums optional assessed_fee_amount only.

    The PRD does not specify a fee formula. This report never invents one.
    """
    _, patients = _census_patients(db, start, end, **filters)
    ids = {p.id for p in patients}
    total = Decimal("0")
    recorded = 0
    if ids:
        rows = db.scalars(select(SocialWorkerAssessment).where(SocialWorkerAssessment.patient_id.in_(ids))).all()
        for row in rows:
            if row.assessed_fee_amount is not None:
                total += Decimal(row.assessed_fee_amount)
                recorded += 1
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "recorded_assessments": recorded,
        "total_assessed_fee_amount": str(total),
        "note": (
            "Room-fee assessment fields are not fully confirmed in the PRD. "
            "This report totals optional assessed_fee_amount values only and does not apply a formula."
        ),
    }


def donations_summary(db: Session, start: date, end: date) -> dict:
    rows = list(
        db.scalars(
            select(Donation).options(joinedload(Donation.category)).where(Donation.date >= start, Donation.date <= end)
        )
        .unique()
        .all()
    )
    by_type: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    total = Decimal("0")
    for row in rows:
        total += Decimal(row.amount)
        by_type[row.type.value] += Decimal(row.amount)
        label = row.category_tag or (row.category.name if row.category else "Uncategorised")
        by_category[label] += Decimal(row.amount)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(rows),
        "total_amount": str(total),
        "by_type": {k: str(v) for k, v in by_type.items()},
        "by_category": {k: str(v) for k, v in by_category.items()},
    }


def petty_cash_report(db: Session, start: date, end: date) -> dict:
    rows = list(
        db.scalars(
            select(PettyCashEntry).where(PettyCashEntry.month >= start.replace(day=1), PettyCashEntry.month <= end)
        ).all()
    )
    budgeted = sum((Decimal(r.budgeted) for r in rows), Decimal("0"))
    actual = sum((Decimal(r.actual) for r in rows), Decimal("0"))
    by_category: dict[str, dict] = {}
    for r in rows:
        key = r.category.value
        bucket = by_category.setdefault(key, {"budgeted": Decimal("0"), "actual": Decimal("0")})
        bucket["budgeted"] += Decimal(r.budgeted)
        bucket["actual"] += Decimal(r.actual)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_budgeted": str(budgeted),
        "total_actual": str(actual),
        "total_balance": str(budgeted - actual),
        "by_category": {
            k: {"budgeted": str(v["budgeted"]), "actual": str(v["actual"]), "balance": str(v["budgeted"] - v["actual"])}
            for k, v in by_category.items()
        },
    }


def admission_summary(db: Session, start: date, end: date) -> dict:
    check_ins = (
        db.scalar(select(func.count(RoomStay.id)).where(RoomStay.check_in_date >= start, RoomStay.check_in_date <= end))
        or 0
    )
    check_outs = (
        db.scalar(
            select(func.count(RoomStay.id)).where(
                RoomStay.check_out_date.is_not(None),
                RoomStay.check_out_date >= start,
                RoomStay.check_out_date <= end,
            )
        )
        or 0
    )
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)
    new_intakes = (
        db.scalar(
            select(func.count(Patient.id)).where(
                Patient.registered_at >= start_dt,
                Patient.registered_at <= end_dt,
            )
        )
        or 0
    )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "check_ins": check_ins,
        "check_outs": check_outs,
        "new_intakes": new_intakes,
    }


REPORT_BUILDERS = {
    "occupancy": occupancy_report,
    "occupancy-trend": occupancy_trend,
    "census": census_report,
    "census-gender": census_by_gender,
    "census-ward": census_by_ward,
    "census-state": census_by_state,
    "new-vs-returning": new_vs_returning,
    "guardian-sibling": guardian_sibling_totals,
    "length-of-stay": length_of_stay,
    "room-rental-income": room_rental_income,
    "donations-summary": donations_summary,
    "petty-cash": petty_cash_report,
    "admission-summary": admission_summary,
}

CENSUS_FILTER_REPORTS = {
    "census",
    "census-gender",
    "census-ward",
    "census-state",
    "new-vs-returning",
    "guardian-sibling",
    "room-rental-income",
}

REPORT_PERMISSION = {
    "occupancy": "reports:occupancy",
    "occupancy-trend": "reports:occupancy",
    "census": "reports:census",
    "census-gender": "reports:census",
    "census-ward": "reports:census",
    "census-state": "reports:census",
    "new-vs-returning": "reports:census",
    "guardian-sibling": "reports:census",
    "length-of-stay": "reports:occupancy",
    "room-rental-income": "reports:finance",
    "donations-summary": "reports:finance",
    "petty-cash": "reports:finance",
    "admission-summary": "reports:admission",
}

REPORT_TITLES = {
    "occupancy": "Daily Occupancy Rate",
    "occupancy-trend": "Occupancy Trend",
    "census": "Patient Census",
    "census-gender": "Census by Gender",
    "census-ward": "Census by Ward/Clinic",
    "census-state": "Census by State",
    "new-vs-returning": "New vs Returning",
    "guardian-sibling": "Guardian and Sibling Totals",
    "length-of-stay": "Length of Stay Breakdown",
    "room-rental-income": "Room Rental Income (assessed amounts only)",
    "donations-summary": "Donation Summary",
    "petty-cash": "Petty Cash Budget vs Actual",
    "admission-summary": "Admission Summary",
}
