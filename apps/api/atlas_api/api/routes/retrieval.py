from fastapi import APIRouter

from atlas_api.schemas import RetrievalRequest, RetrievalResponse
from atlas_api.services.store import store

router = APIRouter()


@router.post("/query", response_model=RetrievalResponse)
def query_memory(payload: RetrievalRequest) -> RetrievalResponse:
    hits = store.search_memories(
        payload.query,
        top_k=payload.top_k,
        memory_types=payload.memory_types,
        tags=payload.tags,
    )
    return RetrievalResponse(query=payload.query, hits=hits)
