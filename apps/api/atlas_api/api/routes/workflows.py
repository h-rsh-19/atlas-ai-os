from fastapi import APIRouter

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import WorkflowDefinition, WorkflowRunCreate, WorkflowRunDetail
from atlas_api.services.store import store

router = APIRouter()


@router.get("/definitions", response_model=list[WorkflowDefinition])
def workflow_definitions() -> list[WorkflowDefinition]:
    return store.workflow_definitions()


@router.get("", response_model=list[WorkflowRunDetail])
def list_workflows() -> list[WorkflowRunDetail]:
    return store.list_workflow_runs()


@router.post("/run", response_model=WorkflowRunDetail)
def run_workflow(payload: WorkflowRunCreate) -> WorkflowRunDetail:
    try:
        return store.run_workflow(payload.workflow_name, payload.inputs)
    except ValueError as exc:
        raise AtlasError(str(exc), status_code=404, code="workflow_not_found") from exc
