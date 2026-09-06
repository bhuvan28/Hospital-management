from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.database import get_db
from app.models.user import User
from app.security.rbac import has_permission
from app.security.tokens import decode_access_token


def _extract_token(request: Request, authorization: str | None) -> str | None:
    settings = get_settings()
    cookie = request.cookies.get(settings.cookie_name)
    if cookie:
        return cookie
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    token = _extract_token(request, authorization)
    if not token:
        raise UnauthorizedError()
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = int(subject)
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Session expired or invalid") from exc
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Session expired or invalid")
    if not user.active:
        raise ForbiddenError("This account is inactive")
    return user


def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise ForbiddenError("You do not have permission to perform this action")
        return user

    return Depends(dependency)
