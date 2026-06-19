from fastapi import APIRouter

from atlas_api.schemas import LabsOverview
from atlas_api.services.labs_service import labs_overview

router = APIRouter()


@router.get("", response_model=LabsOverview)
def get_labs_overview() -> LabsOverview:
    return labs_overview()
