from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger

logger = get_logger("errors")


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, code="not_found")


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409, code="conflict")


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, status_code=403, code="forbidden")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, code="unauthorized")


class ValidationAppError(AppError):
    def __init__(self, message: str = "Please correct the highlighted fields"):
        super().__init__(message, status_code=422, code="validation_error")


def error_payload(message: str, code: str = "error", details: list | None = None) -> dict:
    body: dict = {"error": {"message": message, "code": code}}
    if details:
        body["error"]["details"] = details
    return body


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_payload(exc.message, exc.code))


async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code = "unauthorized" if exc.status_code == 401 else "forbidden" if exc.status_code == 403 else "error"
    return JSONResponse(status_code=exc.status_code, content=error_payload(message, code))


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        loc = " → ".join(str(part) for part in err.get("loc", []) if part != "body")
        details.append({"field": loc, "message": err.get("msg")})
    return JSONResponse(
        status_code=422,
        content=error_payload("Please correct the highlighted fields", "validation_error", details),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", path=str(request.url.path), error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content=error_payload("An unexpected error occurred. Please try again or contact the administrator."),
    )
