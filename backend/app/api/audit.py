from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.database import get_db
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import User

router = APIRouter(prefix="/api/audit-log", tags=["audit"])


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
