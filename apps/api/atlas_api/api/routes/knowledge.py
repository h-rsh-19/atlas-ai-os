from fastapi import APIRouter

from atlas_api.schemas import KnowledgeGraph
from atlas_api.services.store import store

router = APIRouter()


@router.get("/graph", response_model=KnowledgeGraph)
def get_knowledge_graph() -> KnowledgeGraph:
    return store.knowledge_graph()
