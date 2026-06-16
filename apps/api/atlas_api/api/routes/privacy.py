from fastapi import APIRouter

from atlas_api.schemas import (
    ForgetMemoryRequest,
    ForgetMemoryResponse,
    MemoryExport,
    PrivacySettings,
    PrivacySettingsUpdate,
    RedactionPreviewRequest,
    RedactionPreviewResponse,
)
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=PrivacySettings)
def get_privacy_settings() -> PrivacySettings:
    return store.get_privacy_settings()


@router.put("", response_model=PrivacySettings)
def update_privacy_settings(payload: PrivacySettingsUpdate) -> PrivacySettings:
    return store.update_privacy_settings(payload)


@router.post("/redact", response_model=RedactionPreviewResponse)
def redact_preview(payload: RedactionPreviewRequest) -> RedactionPreviewResponse:
    return store.redact_text(payload.text)


@router.get("/export", response_model=MemoryExport)
def export_memory(redacted: bool = True) -> MemoryExport:
    return store.export_memory(redacted=redacted)


@router.post("/forget", response_model=ForgetMemoryResponse)
def forget_memory(payload: ForgetMemoryRequest) -> ForgetMemoryResponse:
    return store.forget_memory(memory_id=payload.memory_id, query=payload.query)
