from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api import audit, auth, dashboard, finance, health, lookups, patients, reports, rooms, users, waitlist
from app.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.core.limiter import limiter
from app.database import SessionLocal
from app.logging_config import configure_logging, get_logger
from app.security.csrf import CSRFMiddleware
from app.seed import run_seed

logger = get_logger("app")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path.startswith("/api/"):
            response.headers["X-Robots-Tag"] = "noindex"
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("startup", environment=settings.app_env)
    if settings.seed_on_startup and settings.app_env != "production":
        db = SessionLocal()
        try:
            run_seed(db)
        finally:
            db.close()
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Self-hosted operations platform for Ronald McDonald House at Hospital Canselor Tuanku Muhriz (HCTM), UKM."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unhandled_error_handler)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(CSRFMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(lookups.router)
    application.include_router(patients.router)
    application.include_router(rooms.router)
    application.include_router(waitlist.router)
    application.include_router(finance.donations_router)
    application.include_router(finance.petty_router)
    application.include_router(finance.meals_router)
    application.include_router(dashboard.router)
    application.include_router(reports.router)
    application.include_router(audit.router)
    return application


app = create_app()
