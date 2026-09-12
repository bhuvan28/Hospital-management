from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction

SENSITIVE_KEYS = {"password", "password_hash", "token", "secret", "csrf"}


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items() if k not in SENSITIVE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def sanitize(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {k: _serialize(v) for k, v in data.items() if k not in SENSITIVE_KEYS}


def changed_field_names(before: dict | None, after: dict | None) -> list[str]:
    before = before or {}
    after = after or {}
    keys = set(before) | set(after)
    return sorted(k for k in keys if k not in SENSITIVE_KEYS and before.get(k) != after.get(k))


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    entity: str,
    entity_id: int,
    action: AuditAction,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    before_clean = sanitize(before)
    after_clean = sanitize(after)
    log = AuditLog(
        user_id=user_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        before_values=before_clean,
        after_values=after_clean,
        changed_fields=changed_field_names(before_clean, after_clean),
    )
    db.add(log)
    return log
