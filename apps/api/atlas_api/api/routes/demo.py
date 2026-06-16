from fastapi import APIRouter

from atlas_api.schemas import DemoFlowStatus
from atlas_api.services.store import store

router = APIRouter()


@router.get("/flow", response_model=DemoFlowStatus)
def demo_flow() -> DemoFlowStatus:
    return store.demo_flow_status()
