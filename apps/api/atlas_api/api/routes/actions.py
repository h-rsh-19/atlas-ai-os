from fastapi import APIRouter, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import ApprovalAction, ApprovalActionCreate, ArtifactRecord
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[ApprovalAction])
def list_actions() -> list[ApprovalAction]:
    return store.list_actions()


@router.post("", response_model=ApprovalAction, status_code=status.HTTP_201_CREATED)
def propose_action(payload: ApprovalActionCreate) -> ApprovalAction:
    return store.propose_action(payload)


@router.post("/{action_id}/approve", response_model=ApprovalAction)
def approve_action(action_id: str) -> ApprovalAction:
    action = store.approve_action(action_id)
    if not action:
        raise AtlasError("Action not found.", status_code=404, code="action_not_found")
    return action


@router.post("/{action_id}/reject", response_model=ApprovalAction)
def reject_action(action_id: str) -> ApprovalAction:
    action = store.reject_action(action_id)
    if not action:
        raise AtlasError("Action not found.", status_code=404, code="action_not_found")
    return action


@router.get("/artifacts", response_model=list[ArtifactRecord])
def list_artifacts() -> list[ArtifactRecord]:
    return store.list_artifacts()
