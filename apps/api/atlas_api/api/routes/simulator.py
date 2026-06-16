from fastapi import APIRouter, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import (
    SimulationAnswerRequest,
    SimulationRun,
    SimulationStartRequest,
    SimulatorScenario,
)
from atlas_api.services.store import store

router = APIRouter()


@router.get("/scenarios", response_model=list[SimulatorScenario])
def scenarios() -> list[SimulatorScenario]:
    return store.simulator_scenarios()


@router.get("", response_model=list[SimulationRun])
def list_runs() -> list[SimulationRun]:
    return store.list_simulations()


@router.post("/start", response_model=SimulationRun, status_code=status.HTTP_201_CREATED)
def start_simulation(payload: SimulationStartRequest) -> SimulationRun:
    try:
        return store.start_simulation(payload)
    except ValueError as exc:
        raise AtlasError(str(exc), status_code=404, code="scenario_not_found") from exc


@router.post("/{run_id}/answer", response_model=SimulationRun)
def answer_simulation(run_id: str, payload: SimulationAnswerRequest) -> SimulationRun:
    run = store.answer_simulation(run_id, payload)
    if not run:
        raise AtlasError("Simulation run not found.", status_code=404, code="simulation_not_found")
    return run
