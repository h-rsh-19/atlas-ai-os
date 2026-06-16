from fastapi import APIRouter
from sqlalchemy import text

from atlas_api import __version__
from atlas_api.core.config import get_settings
from atlas_api.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "version": __version__,
    }


@router.get("/health/db")
def database_health() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("select 1"))
    return {"status": "ok", "database": "reachable"}
