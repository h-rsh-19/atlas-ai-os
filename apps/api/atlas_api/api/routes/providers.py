from fastapi import APIRouter

from atlas_api.core.config import get_settings
from atlas_api.schemas import ProviderHealthResponse
from atlas_api.services.provider_health import provider_health

router = APIRouter()


@router.get("/health", response_model=ProviderHealthResponse)
def health() -> ProviderHealthResponse:
    return provider_health(get_settings())
