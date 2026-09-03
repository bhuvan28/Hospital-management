from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/audit-log", tags=["audit"])


@router.get("")
def list_audit(
    entity: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = require_permission("audit:read"),
):
    stmt = select(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.timestamp.desc())
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all())
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
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
