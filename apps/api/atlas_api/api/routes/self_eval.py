from fastapi import APIRouter

from atlas_api.schemas import SelfEvaluationRequest, SelfEvaluationResponse
from atlas_api.services.store import store

router = APIRouter()


@router.post("", response_model=SelfEvaluationResponse)
def self_evaluate(payload: SelfEvaluationRequest) -> SelfEvaluationResponse:
    return store.self_evaluate(payload)
