from fastapi import APIRouter

from atlas_api.schemas import DashboardSummary
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=DashboardSummary)
def dashboard_summary() -> DashboardSummary:
    return store.dashboard_summary()
