from fastapi import APIRouter, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import (
    EmbeddingReindexResponse,
    MemoryCreate,
    MemoryItem,
    MemoryUpdate,
    RetrievalRequest,
    RetrievalResponse,
)
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[MemoryItem])
def list_memory() -> list[MemoryItem]:
    return store.list_memories()


@router.post("", response_model=MemoryItem, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate) -> MemoryItem:
    return store.create_memory(payload)


@router.post("/search", response_model=RetrievalResponse)
def search_memory(payload: RetrievalRequest) -> RetrievalResponse:
    hits = store.search_memories(
        payload.query,
        top_k=payload.top_k,
        memory_types=payload.memory_types,
        tags=payload.tags,
    )
    return RetrievalResponse(query=payload.query, hits=hits)


@router.post("/embeddings/reindex", response_model=EmbeddingReindexResponse)
def reindex_embeddings() -> EmbeddingReindexResponse:
    return store.reindex_embeddings()


@router.get("/{memory_id}", response_model=MemoryItem)
def get_memory(memory_id: str) -> MemoryItem:
    memory = store.get_memory(memory_id)
    if not memory:
        raise AtlasError("Memory not found.", status_code=404, code="memory_not_found")
    return memory


@router.put("/{memory_id}", response_model=MemoryItem)
def update_memory(memory_id: str, payload: MemoryUpdate) -> MemoryItem:
    memory = store.update_memory(memory_id, payload)
    if not memory:
        raise AtlasError("Memory not found.", status_code=404, code="memory_not_found")
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str) -> None:
    deleted = store.delete_memory(memory_id)
    if not deleted:
        raise AtlasError("Memory not found.", status_code=404, code="memory_not_found")
