from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from atlas_api.core.config import Settings
from atlas_api.schemas import ProviderHealthItem, ProviderHealthResponse


def provider_health(settings: Settings) -> ProviderHealthResponse:
    generation_provider = _normalise_provider(settings.llm_provider)
    embedding_provider = _normalise_provider(settings.embedding_provider)
    timeout_seconds = max(0.2, min(settings.llm_timeout_seconds, 1.5))

    checks = [
        ProviderHealthItem(
            id="deterministic",
            name="Deterministic fallback",
            provider_type="local",
            configured=True,
            active=generation_provider == "deterministic" or embedding_provider == "deterministic",
            reachable=True,
            status="active"
            if generation_provider == "deterministic" or embedding_provider == "deterministic"
            else "available",
            model=settings.llm_model,
            details="Local deterministic generation and embeddings are always available.",
        ),
        _openai_health(settings, generation_provider, embedding_provider, timeout_seconds),
        _local_provider_health(
            id="ollama",
            name="Ollama",
            endpoint=settings.ollama_base_url,
            health_path="/api/tags",
            model=settings.ollama_model,
            active=generation_provider == "ollama" or embedding_provider == "ollama",
            timeout_seconds=timeout_seconds,
        ),
        _local_provider_health(
            id="vllm",
            name="vLLM",
            endpoint=settings.vllm_base_url,
            health_path="/models",
            model=settings.vllm_model,
            active=generation_provider == "vllm" or embedding_provider == "vllm",
            timeout_seconds=timeout_seconds,
        ),
        ProviderHealthItem(
            id="embedding-provider",
            name="Active embedding provider",
            provider_type="embedding",
            configured=True,
            active=True,
            reachable=True if embedding_provider == "deterministic" else None,
            status=embedding_provider,
            model=settings.embedding_model,
            details=(
                f"Atlas will store {settings.embedding_dimensions}-dimension vectors "
                f"using {embedding_provider}."
            ),
        ),
    ]

    return ProviderHealthResponse(
        generation_provider=generation_provider,
        embedding_provider=embedding_provider,
        checks=checks,
    )


def _openai_health(
    settings: Settings,
    generation_provider: str,
    embedding_provider: str,
    timeout_seconds: float,
) -> ProviderHealthItem:
    configured = bool(settings.openai_api_key)
    active = generation_provider == "openai" or embedding_provider == "openai"
    if not configured:
        return ProviderHealthItem(
            id="openai",
            name="OpenAI",
            provider_type="cloud",
            configured=False,
            active=active,
            reachable=None,
            status="missing_key",
            model=settings.openai_chat_model,
            endpoint=settings.openai_base_url,
            details="Set ATLAS_OPENAI_API_KEY to enable OpenAI chat or embeddings.",
        )

    reachable, latency_ms = _get_json(
        f"{settings.openai_base_url.rstrip('/')}/models",
        timeout_seconds=timeout_seconds,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
    )
    return ProviderHealthItem(
        id="openai",
        name="OpenAI",
        provider_type="cloud",
        configured=True,
        active=active,
        reachable=reachable,
        status="reachable" if reachable else "unreachable",
        model=settings.openai_chat_model,
        endpoint=settings.openai_base_url,
        latency_ms=latency_ms,
        details=(
            "OpenAI API key is configured."
            if reachable
            else "OpenAI key is configured, but the health check did not complete."
        ),
    )


def _local_provider_health(
    *,
    id: str,
    name: str,
    endpoint: str,
    health_path: str,
    model: str,
    active: bool,
    timeout_seconds: float,
) -> ProviderHealthItem:
    reachable, latency_ms = _get_json(
        f"{endpoint.rstrip('/')}{health_path}",
        timeout_seconds=timeout_seconds,
    )
    return ProviderHealthItem(
        id=id,
        name=name,
        provider_type="local",
        configured=True,
        active=active,
        reachable=reachable,
        status="reachable" if reachable else "unreachable",
        model=model,
        endpoint=endpoint,
        latency_ms=latency_ms,
        details=(
            f"{name} endpoint responded."
            if reachable
            else f"{name} endpoint did not respond on the configured local URL."
        ),
    )


def _get_json(
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
) -> tuple[bool, int | None]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
        parsed: Any = json.loads(body)
        return isinstance(parsed, dict), round((time.perf_counter() - started) * 1000)
    except (
        OSError,
        TimeoutError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False, None


def _normalise_provider(value: str) -> str:
    provider = value.lower().strip()
    if provider in {"", "test"}:
        return "deterministic"
    return provider
