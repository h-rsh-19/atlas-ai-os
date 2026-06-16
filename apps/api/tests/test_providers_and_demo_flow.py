import json

from fastapi.testclient import TestClient

from atlas_api.core.config import get_settings
from atlas_api.main import app
from atlas_api.services import embeddings as embeddings_module
from atlas_api.services import llm as llm_module
from atlas_api.services.embeddings import OpenAIEmbeddingProvider, get_embedding_provider
from atlas_api.services.llm import (
    DeterministicLLMProvider,
    FallbackLLMProvider,
    GroundedChatOutput,
    OpenAIChatProvider,
    get_llm_provider,
    grounded_chat_template,
)

client = TestClient(app)


def test_deterministic_provider_layers_return_structured_results() -> None:
    settings = get_settings()
    llm = get_llm_provider(settings)
    embeddings = get_embedding_provider(settings)

    generated = llm.generate_json(
        template=grounded_chat_template(),
        variables={"message": "hello", "context": "", "profile": {}, "evidence": []},
        fallback={
            "answer": "local answer",
            "confidence": 0.5,
            "assumptions": [],
            "verification_needed": [],
        },
        output_model=GroundedChatOutput,
    )
    vector = embeddings.embed("Atlas retrieval evidence")

    assert generated.content["answer"] == "local answer"
    assert generated.prompt_version == "grounded-chat:v2"
    assert generated.fallback_used is False
    assert vector.provider == "deterministic"
    assert len(vector.vector) == settings.embedding_dimensions


def test_openai_compatible_chat_provider_path_is_validated(monkeypatch) -> None:
    def fake_post_json(url, payload, *, headers, timeout_seconds):
        assert url.endswith("/chat/completions")
        assert payload["response_format"] == {"type": "json_object"}
        assert headers["Authorization"] == "Bearer test-key"
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "answer": "Provider answer",
                                "confidence": 0.91,
                                "assumptions": ["Used supplied evidence"],
                                "verification_needed": [],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(llm_module, "_post_json", fake_post_json)
    provider = OpenAIChatProvider(
        provider_id="openai",
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-chat-model",
        timeout_seconds=1,
    )

    result = provider.generate_json(
        template=grounded_chat_template(),
        variables={"message": "hello", "context": "", "profile": {}, "evidence": []},
        fallback={
            "answer": "fallback",
            "confidence": 0.5,
            "assumptions": [],
            "verification_needed": [],
        },
        output_model=GroundedChatOutput,
    )

    assert result.provider == "openai"
    assert result.fallback_used is False
    assert result.content["answer"] == "Provider answer"


def test_invalid_provider_json_falls_back_with_error(monkeypatch) -> None:
    def fake_post_json(url, payload, *, headers, timeout_seconds):
        return {"choices": [{"message": {"content": json.dumps({"confidence": 2})}}]}

    monkeypatch.setattr(llm_module, "_post_json", fake_post_json)
    primary = OpenAIChatProvider(
        provider_id="openai",
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-chat-model",
        timeout_seconds=1,
    )
    provider = FallbackLLMProvider(primary, DeterministicLLMProvider())

    result = provider.generate_json(
        template=grounded_chat_template(),
        variables={"message": "hello", "context": "", "profile": {}, "evidence": []},
        fallback={
            "answer": "validated fallback",
            "confidence": 0.4,
            "assumptions": [],
            "verification_needed": ["Check provider output schema"],
        },
        output_model=GroundedChatOutput,
    )

    assert result.fallback_used is True
    assert result.provider == "openai:fallback:deterministic"
    assert result.content["answer"] == "validated fallback"
    assert result.errors


def test_openai_compatible_embedding_provider_path_is_mocked(monkeypatch) -> None:
    def fake_post_json(url, payload, *, timeout_seconds, headers=None):
        assert url.endswith("/embeddings")
        assert payload["model"] == "test-embedding-model"
        assert headers == {"Authorization": "Bearer test-key"}
        return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    monkeypatch.setattr(embeddings_module, "_post_json", fake_post_json)
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-embedding-model",
        dimensions=3,
        timeout_seconds=1,
    )

    result = provider.embed("Atlas provider test")

    assert result.provider == "openai"
    assert result.model == "test-embedding-model"
    assert result.vector == [0.1, 0.2, 0.3]


def test_memory_embedding_reindex_records_provider_metadata() -> None:
    created = client.post(
        "/api/memory",
        json={
            "source_title": "Embedding provider note",
            "source_type": "note",
            "memory_type": "learning",
            "title": "Embedding provider seam",
            "content": "Atlas can swap deterministic embeddings for configured providers.",
            "tags": ["embedding"],
            "importance": 0.7,
        },
    )
    reindexed = client.post("/api/memory/embeddings/reindex")
    fetched = client.get(f"/api/memory/{created.json()['id']}")

    assert created.status_code == 201
    assert reindexed.status_code == 200
    assert reindexed.json()["reindexed_count"] >= 1
    assert fetched.status_code == 200
    assert fetched.json()["metadata"]["_embedding_provider"].startswith("deterministic")


def test_demo_flow_reports_live_golden_path_state() -> None:
    response = client.get("/api/demo/flow")

    assert response.status_code == 200
    body = response.json()
    assert body["current_mode"].startswith("local deterministic prototype")
    assert body["steps"][0]["id"] == "resume_upload"
    assert body["next_step"]
    assert 0 <= body["completion_percent"] <= 100


def test_demo_seed_reset_and_script_flow() -> None:
    seeded = client.post("/api/demo/seed")
    script = client.get("/api/demo/script")
    reset = client.post("/api/demo/reset")

    assert seeded.status_code == 200
    assert seeded.json()["flow"]["completion_percent"] == 100
    assert "artifact_action" in " ".join(seeded.json()["created"])
    assert script.status_code == 200
    assert "Atlas recruiter demo script" in script.json()["script"]
    assert reset.status_code == 200
    assert reset.json()["message"] == "Reset Atlas demo-owned state."
    assert reset.json()["deleted"]
