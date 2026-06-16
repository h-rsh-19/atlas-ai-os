from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from atlas_api.core.config import Settings

TOKEN_RE = re.compile(r"[a-zA-Z0-9+#.\-]+")


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    provider: str
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    id: str
    model: str
    dimensions: int

    def embed(self, text: str) -> EmbeddingResult:
        """Return one vector for a text input."""


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def deterministic_embed_text(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_text(text: str, dimensions: int) -> list[float]:
    """Backward-compatible deterministic embedding helper."""
    return deterministic_embed_text(text, dimensions)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    limit = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(limit))


class DeterministicEmbeddingProvider:
    def __init__(
        self,
        *,
        model: str = "atlas-deterministic-embedding-v1",
        dimensions: int = 1536,
    ) -> None:
        self.id = "deterministic"
        self.model = model
        self.dimensions = dimensions

    def embed(self, text: str) -> EmbeddingResult:
        vector = deterministic_embed_text(text, self.dimensions)
        return EmbeddingResult(
            vector=vector,
            provider=self.id,
            model=self.model,
            dimensions=len(vector),
        )


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self.id = "openai"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str) -> EmbeddingResult:
        if not self.api_key:
            raise RuntimeError("ATLAS_OPENAI_API_KEY is required for OpenAI embeddings.")
        payload: dict[str, object] = {"model": self.model, "input": text}
        if self.dimensions:
            payload["dimensions"] = self.dimensions
        response = _post_json(
            f"{self.base_url}/embeddings",
            payload,
            timeout_seconds=self.timeout_seconds,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        vector = response["data"][0]["embedding"]
        if not isinstance(vector, list):
            raise RuntimeError("Embedding response did not include a vector.")
        return EmbeddingResult(
            vector=[float(value) for value in vector],
            provider=self.id,
            model=self.model,
            dimensions=len(vector),
        )


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self.id = provider_id
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str) -> EmbeddingResult:
        response = _post_json(
            f"{self.base_url}/embeddings",
            {"model": self.model, "input": text},
            timeout_seconds=self.timeout_seconds,
        )
        vector = response["data"][0]["embedding"]
        if not isinstance(vector, list):
            raise RuntimeError("Embedding response did not include a vector.")
        return EmbeddingResult(
            vector=[float(value) for value in vector],
            provider=self.id,
            model=self.model,
            dimensions=len(vector),
        )


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self.id = "ollama"
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str) -> EmbeddingResult:
        response = _post_json(
            f"{self.base_url}/api/embeddings",
            {"model": self.model, "prompt": text},
            timeout_seconds=self.timeout_seconds,
        )
        vector = response.get("embedding")
        if not isinstance(vector, list):
            raise RuntimeError("Ollama embedding response did not include a vector.")
        return EmbeddingResult(
            vector=[float(value) for value in vector],
            provider=self.id,
            model=self.model,
            dimensions=len(vector),
        )


class FallbackEmbeddingProvider:
    def __init__(
        self,
        primary: EmbeddingProvider,
        fallback: DeterministicEmbeddingProvider,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.id = primary.id
        self.model = primary.model
        self.dimensions = primary.dimensions

    def embed(self, text: str) -> EmbeddingResult:
        try:
            return self.primary.embed(text)
        except (RuntimeError, urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError):
            result = self.fallback.embed(text)
            return EmbeddingResult(
                vector=result.vector,
                provider=f"{self.primary.id}:fallback:{self.fallback.id}",
                model=result.model,
                dimensions=result.dimensions,
            )


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    fallback = DeterministicEmbeddingProvider(
        model="atlas-deterministic-embedding-v1",
        dimensions=settings.embedding_dimensions,
    )
    provider = settings.embedding_provider.lower().strip()
    if provider in {"", "deterministic", "test"}:
        return DeterministicEmbeddingProvider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    if provider == "openai":
        primary = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackEmbeddingProvider(primary, fallback)
    if provider == "ollama":
        primary = OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model or settings.ollama_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackEmbeddingProvider(primary, fallback)
    if provider == "vllm":
        primary = OpenAICompatibleEmbeddingProvider(
            provider_id="vllm",
            base_url=settings.vllm_base_url,
            model=settings.embedding_model or settings.vllm_model,
            dimensions=settings.embedding_dimensions,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackEmbeddingProvider(primary, fallback)
    return fallback


def _post_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("Provider response was not a JSON object.")
    return parsed
