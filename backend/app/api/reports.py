from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ForbiddenError, NotFoundError
from app.database import get_db
from app.models.user import User
from app.security.rbac import has_permission
from app.services.exports import to_excel, to_pdf
from app.services.reports import REPORT_BUILDERS, REPORT_PERMISSION, REPORT_TITLES

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    today = date.today()
    return start or today.replace(day=1), end or today


def _run(name: str, db: Session, user: User, start: date, end: date):
    if name not in REPORT_BUILDERS:
        raise NotFoundError("Unknown report")
    permission = REPORT_PERMISSION[name]
    if not has_permission(user.role, permission):
        raise ForbiddenError("You do not have permission to view this report")
    builder = REPORT_BUILDERS[name]
    if name == "occupancy-trend":
        return builder(db, start, end)
    return builder(db, start, end)


@router.get("/occupancy")
def occupancy(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    return _run("occupancy", db, user, s, e)


@router.get("/census")
def census(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    return _run("census", db, user, s, e)


@router.get("/donations-summary")
def donations_summary(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    return _run("donations-summary", db, user, s, e)


@router.get("/admission-summary")
def admission_summary(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    return _run("admission-summary", db, user, s, e)


@router.get("/{report_name}")
def generic_report(
    report_name: str,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    return _run(report_name, db, user, s, e)


@router.get("/{report_name}/export")
def export_report(
    report_name: str,
    start: date | None = None,
    end: date | None = None,
    format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s, e = _range(start, end)
    data = _run(report_name, db, user, s, e)
    title = REPORT_TITLES.get(report_name, report_name)
    if format == "pdf":
        content = to_pdf(title, data)
        media = "application/pdf"
        filename = f"{report_name}.pdf"
    else:
        content = to_excel(title, data)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{report_name}.xlsx"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
