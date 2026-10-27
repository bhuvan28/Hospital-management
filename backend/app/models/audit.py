from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.enums import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", native_enum=False, length=20),
        nullable=False,
    )
    before_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    changed_fields: Mapped[list[str] | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user = relationship("User", back_populates="audit_logs")


class AuditLogImmutableError(RuntimeError):
    """Audit rows cannot be changed or deleted through the application."""


@event.listens_for(AuditLog, "before_update")
def _reject_audit_update(_mapper, _connection, _target: AuditLog) -> None:
    raise AuditLogImmutableError("Audit logs are immutable")


@event.listens_for(AuditLog, "before_delete")
def _reject_audit_delete(_mapper, _connection, _target: AuditLog) -> None:
    raise AuditLogImmutableError("Audit logs are immutable")
