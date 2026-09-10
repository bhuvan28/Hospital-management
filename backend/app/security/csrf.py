"""Double-submit CSRF protection for cookie-authenticated mutating requests.

Bearer-token API clients skip CSRF. Cross-site cookie posts must send
X-CSRF-Token matching the non-httpOnly CSRF cookie issued at login.
"""

from __future__ import annotations

import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.core.errors import error_payload

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_PATHS = frozenset(
    {
        "/api/auth/login",
        "/api/health",
        "/api/health/ready",
    }
)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    settings = get_settings()
    value = token or generate_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=value,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return value


def clear_csrf_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.csrf_cookie_name, path="/")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in SAFE_METHODS or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        authorization = request.headers.get("authorization") or ""
        if authorization.lower().startswith("bearer "):
            return await call_next(request)

        settings = get_settings()
        session_cookie = request.cookies.get(settings.cookie_name)
        if not session_cookie:
            return await call_next(request)

        cookie_token = request.cookies.get(settings.csrf_cookie_name) or ""
        header_token = request.headers.get("x-csrf-token") or ""
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content=error_payload("CSRF validation failed", "csrf"),
            )
        return await call_next(request)
