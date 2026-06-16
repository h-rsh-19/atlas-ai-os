from fastapi import APIRouter, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import DecisionCreate, DecisionEntry, DecisionUpdate
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[DecisionEntry])
def list_decisions() -> list[DecisionEntry]:
    return store.list_decisions()


@router.post("", response_model=DecisionEntry, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate) -> DecisionEntry:
    return store.create_decision(payload)


@router.put("/{decision_id}", response_model=DecisionEntry)
def update_decision(decision_id: str, payload: DecisionUpdate) -> DecisionEntry:
    decision = store.update_decision(decision_id, payload)
    if not decision:
        raise AtlasError("Decision not found.", status_code=404, code="decision_not_found")
    return decision
