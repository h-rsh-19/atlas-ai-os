from fastapi import APIRouter

from atlas_api.schemas import EvaluationPrompt, EvaluationRun
from atlas_api.services.store import store

router = APIRouter()


@router.get("/prompts", response_model=list[EvaluationPrompt])
def list_evaluation_prompts() -> list[EvaluationPrompt]:
    return store.evaluation_prompts()


@router.get("", response_model=list[EvaluationRun])
def list_evaluation_runs() -> list[EvaluationRun]:
    return store.list_evaluation_runs()


@router.post("/run", response_model=EvaluationRun)
def run_evaluations() -> EvaluationRun:
    return store.run_evaluations()
