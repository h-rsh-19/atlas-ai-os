from fastapi import APIRouter

from atlas_api.schemas import (
    DemoFlowStatus,
    DemoResetResponse,
    DemoRunStepResponse,
    DemoScriptResponse,
    DemoSeedResponse,
)
from atlas_api.services.store import store

router = APIRouter()


@router.get("/flow", response_model=DemoFlowStatus)
def demo_flow() -> DemoFlowStatus:
    return store.demo_flow_status()


@router.post("/seed", response_model=DemoSeedResponse)
def seed_demo() -> DemoSeedResponse:
    return store.seed_demo_state()


@router.post("/run-next", response_model=DemoRunStepResponse)
def run_next_demo_step() -> DemoRunStepResponse:
    return store.run_next_demo_step()


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo() -> DemoResetResponse:
    return store.reset_demo_state()


@router.get("/script", response_model=DemoScriptResponse)
def demo_script() -> DemoScriptResponse:
    return store.recruiter_demo_script()
