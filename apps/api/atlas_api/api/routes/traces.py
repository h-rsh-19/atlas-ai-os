from fastapi import APIRouter

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import TraceRun
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[TraceRun])
def list_traces() -> list[TraceRun]:
    return store.list_traces()


@router.get("/{trace_id}", response_model=TraceRun)
def get_trace(trace_id: str) -> TraceRun:
    trace = store.get_trace(trace_id)
    if not trace:
        raise AtlasError("Trace not found.", status_code=404, code="trace_not_found")
    return trace
