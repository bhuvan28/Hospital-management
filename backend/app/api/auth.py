from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, UnauthorizedError
from app.core.limiter import limiter
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


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.active:
        raise ForbiddenError("This account is inactive")
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    _set_session_cookies(response, token)
    set_csrf_cookie(response)
    return LoginResponse(user=_user_payload(user))


@router.post("/logout")
def logout(response: Response):
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
    write_audit(
        db,
        user_id=user.id,
        entity="User",
        entity_id=user.id,
        action=AuditAction.UPDATE,
        after={"password_changed": True},
    )
    db.commit()
    token = create_access_token(str(user.id), extra={"role": user.role.value})
    _set_session_cookies(response, token)
    set_csrf_cookie(response)
    return {"message": "Password updated"}
