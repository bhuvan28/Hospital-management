from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, LockedError, UnauthorizedError
from app.core.limiter import limiter
from app.core.lockout import clear_failures, is_locked, record_failure
from app.database import get_db
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, TokenUser
from app.security.csrf import clear_csrf_cookie, set_csrf_cookie
from app.security.hashing import hash_password, verify_password
from app.security.rbac import navigation_for, permissions_for
from app.security.tokens import create_access_token
from app.services.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_payload(user: User) -> TokenUser:
    return TokenUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        active=user.active,
        permissions=permissions_for(user.role),
        navigation=navigation_for(user.role),
    )


def _set_session_cookies(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _issue_session(response: Response, user: User) -> None:
    token = create_access_token(
        str(user.id),
        extra={"role": user.role.value, "epoch": user.session_epoch},
    )
    _set_session_cookies(response, token)
    set_csrf_cookie(response)


def _audit_auth(
    db: Session,
    *,
    action: AuditAction,
    user: User | None,
    email: str,
    reason: str | None = None,
) -> None:
    after: dict = {"email": email}
    if reason:
        after["reason"] = reason
    write_audit(
        db,
        user_id=user.id if user else None,
        entity="User",
        entity_id=user.id if user else 0,
        action=action,
        after=after,
    )
    db.commit()


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if is_locked(email):
        user = db.scalar(select(User).where(User.email == email))
        _audit_auth(db, action=AuditAction.LOGIN_FAILED, user=user, email=email, reason="locked")
        raise LockedError()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        locked = record_failure(email)
        _audit_auth(
            db,
            action=AuditAction.LOGIN_FAILED,
            user=user,
            email=email,
            reason="locked" if locked else "invalid_credentials",
        )
        if locked:
            raise LockedError()
        raise UnauthorizedError("Invalid email or password")
    if not user.active:
        record_failure(email)
        _audit_auth(db, action=AuditAction.LOGIN_FAILED, user=user, email=email, reason="inactive")
        raise ForbiddenError("This account is inactive")
    clear_failures(email)
    _audit_auth(db, action=AuditAction.LOGIN, user=user, email=user.email)
    _issue_session(response, user)
    return LoginResponse(user=_user_payload(user))


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        actor = get_current_user(request, db, request.headers.get("authorization"))
        _audit_auth(db, action=AuditAction.LOGOUT, user=actor, email=actor.email)
    except (UnauthorizedError, ForbiddenError):
        pass
    settings = get_settings()
    response.delete_cookie(settings.cookie_name, path="/")
    clear_csrf_cookie(response)
    return {"message": "Signed out"}


@router.get("/me", response_model=TokenUser)
def me(user: User = Depends(get_current_user)):
    return _user_payload(user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise ConflictError("New password must be different from the current password")
    user.password_hash = hash_password(payload.new_password)
    user.session_epoch = (user.session_epoch or 0) + 1
    write_audit(
        db,
        user_id=user.id,
        entity="User",
        entity_id=user.id,
        action=AuditAction.UPDATE,
        after={"password_changed": True},
    )
    db.commit()
    _issue_session(response, user)
    return {"message": "Password updated"}
