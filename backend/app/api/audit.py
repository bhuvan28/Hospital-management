from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.database import get_db
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import User
from app.services.exports import to_excel_table

router = APIRouter(prefix="/api/audit-log", tags=["audit"])


def _audit_query(
    *,
    entity: str | None,
    user_id: int | None,
    action: str | None,
    start: date | None,
    end: date | None,
) -> Select:
    stmt = select(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.timestamp.desc())
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        try:
            stmt = stmt.where(AuditLog.action == AuditAction(action))
        except ValueError:
            stmt = stmt.where(AuditLog.id == -1)
    if start:
        stmt = stmt.where(AuditLog.timestamp >= datetime.combine(start, time.min, tzinfo=timezone.utc))
    if end:
        stmt = stmt.where(AuditLog.timestamp <= datetime.combine(end, time.max, tzinfo=timezone.utc))
    return stmt


@router.get("")
def list_audit(
    entity: str | None = None,
    user_id: int | None = None,
    action: str | None = None,
    start: date | None = None,
    end: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = require_permission("audit:read"),
):
    stmt = _audit_query(entity=entity, user_id=user_id, action=action, start=start, end=end)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all())
    pages = (total + page_size - 1) // page_size if total else 0
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "user_name": row.user.name if row.user else None,
                "entity": row.entity,
                "entity_id": row.entity_id,
                "action": row.action.value,
                "before_values": row.before_values,
                "after_values": row.after_values,
                "changed_fields": row.changed_fields,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in items
        ],
    }


@router.get("/export")
def export_audit(
    entity: str | None = None,
    user_id: int | None = None,
    action: str | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("audit:read"),
):
    stmt = _audit_query(entity=entity, user_id=user_id, action=action, start=start, end=end)
    items = list(db.scalars(stmt.limit(1000)).unique().all())
    content = to_excel_table(
        "Audit Log",
        "Metadata only. Before/after snapshots stay in the on-screen log and are not exported.",
        ["When", "User", "Entity", "ID", "Action", "Changed fields"],
        [
            [
                row.timestamp.isoformat() if row.timestamp else "",
                row.user.name if row.user else "",
                row.entity,
                row.entity_id,
                row.action.value,
                ", ".join(row.changed_fields or []),
            ]
            for row in items
        ],
        summary=[("exported_rows", len(items))],
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="RMH-HCTM-UKM-audit-log.xlsx"'},
    )
