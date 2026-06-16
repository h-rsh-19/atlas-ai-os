from fastapi import APIRouter

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import ModelProvider, PluginManifest, PluginUpdate
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[PluginManifest])
def list_plugins() -> list[PluginManifest]:
    return store.list_plugins()


@router.put("/{plugin_id}", response_model=PluginManifest)
def update_plugin(plugin_id: str, payload: PluginUpdate) -> PluginManifest:
    plugin = store.update_plugin(plugin_id, payload)
    if not plugin:
        raise AtlasError("Plugin not found.", status_code=404, code="plugin_not_found")
    return plugin


@router.get("/models/providers", response_model=list[ModelProvider])
def model_providers() -> list[ModelProvider]:
    return store.model_providers()
