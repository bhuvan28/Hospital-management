from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": "rmh-hctm-ukm-backend",
        "environment": settings.app_env,
    }


@router.get("/api/health/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
