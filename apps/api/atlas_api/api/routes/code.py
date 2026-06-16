from fastapi import APIRouter, Query

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import CodeAnalysisResult, CodeGraph, CodeRiskReport, CodeSymbol
from atlas_api.services.store import store

router = APIRouter()


@router.post("/analyze/{project_id}", response_model=CodeAnalysisResult)
def analyze_project(project_id: str) -> CodeAnalysisResult:
    result = store.analyze_codebase(project_id)
    if not result:
        raise AtlasError("Project not found.", status_code=404, code="project_not_found")
    return result


@router.get("/symbols", response_model=list[CodeSymbol])
def list_symbols(
    project_id: str | None = None,
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CodeSymbol]:
    return store.list_code_symbols(project_id=project_id, query=query, limit=limit)


@router.get("/graph/{project_id}", response_model=CodeGraph)
def get_graph(project_id: str) -> CodeGraph:
    graph = store.get_code_graph(project_id)
    if not graph:
        raise AtlasError(
            "Code graph not found. Run analysis first.",
            status_code=404,
            code="graph_not_found",
        )
    return graph


@router.get("/risks/{project_id}", response_model=CodeRiskReport)
def get_risks(project_id: str) -> CodeRiskReport:
    report = store.get_code_risks(project_id)
    if not report:
        raise AtlasError(
            "Code risk report not found. Run analysis first.",
            status_code=404,
            code="risks_not_found",
        )
    return report
