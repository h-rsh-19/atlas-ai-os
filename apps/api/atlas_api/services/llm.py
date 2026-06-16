from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from atlas_api.core.config import Settings


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: str
    system: str
    user: str

    def render(self, variables: dict[str, Any]) -> tuple[str, str]:
        rendered_system = self.system.format(**_TemplateVars(variables))
        rendered_user = self.user.format(**_TemplateVars(variables))
        return rendered_system, rendered_user


@dataclass(frozen=True)
class LLMResult:
    content: dict[str, Any]
    provider: str
    model: str
    prompt_version: str
    latency_ms: int = 0
    fallback_used: bool = False
    errors: list[str] = field(default_factory=list)


class LLMProvider(Protocol):
    id: str
    model: str

    def generate_json(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, Any],
        fallback: dict[str, Any],
    ) -> LLMResult:
        """Generate a structured JSON object from a prompt template."""


class DeterministicLLMProvider:
    def __init__(self, *, model: str = "atlas-deterministic-v1") -> None:
        self.id = "deterministic"
        self.model = model

    def generate_json(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, Any],
        fallback: dict[str, Any],
    ) -> LLMResult:
        return LLMResult(
            content=dict(fallback),
            provider=self.id,
            model=self.model,
            prompt_version=f"{template.id}:{template.version}",
            fallback_used=True,
        )


class OpenAIChatProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.id = provider_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_json(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, Any],
        fallback: dict[str, Any],
    ) -> LLMResult:
        if self.id == "openai" and not self.api_key:
            raise RuntimeError("ATLAS_OPENAI_API_KEY is required for OpenAI generation.")
        system_prompt, user_prompt = template.render(variables)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        response = _post_json(
            f"{self.base_url}/chat/completions",
            payload,
            headers=headers,
            timeout_seconds=self.timeout_seconds,
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("Chat provider returned no choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Chat provider returned no JSON content.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("Chat provider JSON content was not an object.")
        return LLMResult(
            content=parsed,
            provider=self.id,
            model=self.model,
            prompt_version=f"{template.id}:{template.version}",
        )


class OllamaChatProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.id = "ollama"
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_json(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, Any],
        fallback: dict[str, Any],
    ) -> LLMResult:
        system_prompt, user_prompt = template.render(variables)
        response = _post_json(
            f"{self.base_url}/api/chat",
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            headers={"Content-Type": "application/json"},
            timeout_seconds=self.timeout_seconds,
        )
        message = response.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise RuntimeError("Ollama returned no JSON content.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("Ollama JSON content was not an object.")
        return LLMResult(
            content=parsed,
            provider=self.id,
            model=self.model,
            prompt_version=f"{template.id}:{template.version}",
        )


class FallbackLLMProvider:
    def __init__(self, primary: LLMProvider, fallback: DeterministicLLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.id = primary.id
        self.model = primary.model

    def generate_json(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, Any],
        fallback: dict[str, Any],
    ) -> LLMResult:
        try:
            return self.primary.generate_json(
                template=template,
                variables=variables,
                fallback=fallback,
            )
        except (
            RuntimeError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
        ) as exc:
            deterministic = self.fallback.generate_json(
                template=template,
                variables=variables,
                fallback=fallback,
            )
            return LLMResult(
                content=deterministic.content,
                provider=f"{self.primary.id}:fallback:{deterministic.provider}",
                model=deterministic.model,
                prompt_version=deterministic.prompt_version,
                fallback_used=True,
                errors=[str(exc)],
            )


def get_llm_provider(settings: Settings) -> LLMProvider:
    fallback = DeterministicLLMProvider(model="atlas-deterministic-v1")
    provider = settings.llm_provider.lower().strip()
    if provider in {"", "deterministic", "test"}:
        return DeterministicLLMProvider(model=settings.llm_model)
    if provider == "openai":
        primary = OpenAIChatProvider(
            provider_id="openai",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_chat_model or settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackLLMProvider(primary, fallback)
    if provider == "ollama":
        primary = OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model or settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackLLMProvider(primary, fallback)
    if provider == "vllm":
        primary = OpenAIChatProvider(
            provider_id="vllm",
            api_key=None,
            base_url=settings.vllm_base_url,
            model=settings.vllm_model or settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        return FallbackLLMProvider(primary, fallback)
    return fallback


def grounded_chat_template() -> PromptTemplate:
    return PromptTemplate(
        id="grounded-chat",
        version="v2",
        system=(
            "You are Atlas, a local-first personal AI assistant. Answer only from "
            "the supplied profile, user context, and retrieved memories. Return JSON "
            "with keys answer, confidence, assumptions, and verification_needed."
        ),
        user=(
            "User message:\n{message}\n\nAdditional context:\n{context}\n\n"
            "Profile:\n{profile}\n\nRetrieved evidence:\n{evidence}\n"
        ),
    )


def workflow_template() -> PromptTemplate:
    return PromptTemplate(
        id="workflow-json",
        version="v2",
        system=(
            "You are Atlas running a named workflow. Use only supplied evidence. "
            "Return a compact JSON object with practical outputs and an evidence list."
        ),
        user=(
            "Workflow: {workflow_name}\nInputs: {inputs}\nProfile: {profile}\n"
            "Retrieved evidence: {evidence}\nFallback draft: {fallback}\n"
        ),
    )


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError("Provider response was not a JSON object.")
    return parsed


class _TemplateVars(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
