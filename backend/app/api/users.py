from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.errors import ConflictError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.security.hashing import hash_password
from app.services.audit import write_audit

router = APIRouter(prefix="/api/users", tags=["users"])


def _public(user: User) -> UserOut:
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = require_permission("users:manage"),
):
    return [_public(u) for u in db.scalars(select(User).order_by(User.name)).all()]


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("users:manage"),
):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise ConflictError("A user with this email already exists")
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="User",
        entity_id=user.id,
        action=AuditAction.CREATE,
        after={"name": user.name, "email": user.email, "role": user.role.value, "active": user.active},
    )
    db.commit()
    db.refresh(user)
    return _public(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("users:manage"),
):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    before = {"name": user.name, "email": user.email, "role": user.role.value, "active": user.active}
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        clash = db.scalar(select(User).where(User.email == data["email"].lower(), User.id != user.id))
        if clash:
            raise ConflictError("A user with this email already exists")
        data["email"] = data["email"].lower()
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    becoming_inactive = "active" in data and data["active"] is False and user.active
    becoming_active = "active" in data and data["active"] is True and not user.active
    for key, value in data.items():
        setattr(user, key, value)
    if becoming_inactive:
        action = AuditAction.DEACTIVATE
    elif becoming_active:
        action = AuditAction.ACTIVATE
    else:
        action = AuditAction.UPDATE
    write_audit(
        db,
        user_id=actor.id,
        entity="User",
        entity_id=user.id,
        action=action,
        before=before,
        after={"name": user.name, "email": user.email, "role": user.role.value, "active": user.active},
    )
    db.commit()
    db.refresh(user)
    return _public(user)
