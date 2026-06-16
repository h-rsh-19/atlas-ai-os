from fastapi.testclient import TestClient

from atlas_api.core.config import get_settings
from atlas_api.main import app
from atlas_api.services.embeddings import get_embedding_provider
from atlas_api.services.llm import get_llm_provider, grounded_chat_template

client = TestClient(app)


def test_deterministic_provider_layers_return_structured_results() -> None:
    settings = get_settings()
    llm = get_llm_provider(settings)
    embeddings = get_embedding_provider(settings)

    generated = llm.generate_json(
        template=grounded_chat_template(),
        variables={"message": "hello", "context": "", "profile": {}, "evidence": []},
        fallback={"answer": "local answer", "confidence": 0.5},
    )
    vector = embeddings.embed("Atlas retrieval evidence")

    assert generated.content["answer"] == "local answer"
    assert generated.prompt_version == "grounded-chat:v2"
    assert vector.provider == "deterministic"
    assert len(vector.vector) == settings.embedding_dimensions


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
