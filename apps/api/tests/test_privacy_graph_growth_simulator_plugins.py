from fastapi.testclient import TestClient

from atlas_api.main import app

client = TestClient(app)


def test_privacy_settings_redaction_export_and_forget() -> None:
    memory = client.post(
        "/api/memory",
        json={
            "source_title": "Sensitive note",
            "source_type": "note",
            "memory_type": "note",
            "title": "Temporary private fact",
            "content": "Email me at person@example.com with token: sk-testsecret1234567890.",
            "tags": ["privacy"],
            "importance": 0.6,
        },
    ).json()

    settings = client.get("/api/privacy")
    redact = client.post(
        "/api/privacy/redact",
        json={"text": "Contact person@example.com and token: sk-testsecret1234567890"},
    )
    exported = client.get("/api/privacy/export?redacted=true")
    forgotten = client.post("/api/privacy/forget", json={"memory_id": memory["id"]})

    assert settings.status_code == 200
    assert redact.status_code == 200
    assert "person@example.com" not in redact.json()["redacted_text"]
    assert exported.status_code == 200
    assert exported.json()["redacted"] is True
    assert forgotten.status_code == 200
    assert forgotten.json()["deleted_count"] == 1


def test_decision_journal_knowledge_graph_timeline_and_skill_tree() -> None:
    decision = client.post(
        "/api/decisions",
        json={
            "title": "Use FastAPI for Atlas API",
            "decision": "Use FastAPI as the backend framework.",
            "alternatives": ["Django", "Express"],
            "tradeoffs": ["Fast iteration", "Typed API contracts"],
            "reason": "Atlas needs async-friendly typed API routes.",
            "tags": ["FastAPI", "backend"],
        },
    )
    graph = client.get("/api/knowledge/graph")
    timeline = client.get("/api/growth/timeline")
    skills = client.get("/api/growth/skills")

    assert decision.status_code == 201
    assert decision.json()["memory_id"]
    assert graph.status_code == 200
    assert any(node["kind"] == "decision" for node in graph.json()["nodes"])
    assert timeline.status_code == 200
    assert any(event["event_type"] == "decision" for event in timeline.json())
    assert skills.status_code == 200
    assert skills.json()["skills"]


def test_self_evaluation_flags_grounding_and_simulator_scores_answer() -> None:
    self_eval = client.post(
        "/api/self-eval",
        json={
            "prompt": "Explain Atlas",
            "output": "Atlas uses memory citations and approval traces.",
            "citations": [
                {
                    "source_id": "src_test",
                    "title": "Atlas spec",
                    "uri": "docs/product-spec.md",
                    "snippet": "Atlas uses memory citations and approval traces.",
                }
            ],
        },
    )
    scenarios = client.get("/api/simulator/scenarios").json()
    run = client.post("/api/simulator/start", json={"scenario_id": scenarios[0]["id"]})
    answered = client.post(
        f"/api/simulator/{run.json()['id']}/answer",
        json={
            "answer": (
                "I would describe architecture boundaries, privacy approvals, trace evidence, "
                "risk checks, tests, and failure modes."
            )
        },
    )

    assert self_eval.status_code == 200
    assert self_eval.json()["grounded"] is True
    assert self_eval.json()["trace_id"]
    assert run.status_code == 201
    assert answered.status_code == 200
    assert answered.json()["evaluation"]["score"] > 0


def test_plugin_registry_and_model_providers_are_available() -> None:
    plugins = client.get("/api/plugins")
    providers = client.get("/api/plugins/models/providers")
    updated = client.put("/api/plugins/github", json={"enabled": True})

    assert plugins.status_code == 200
    assert any(plugin["id"] == "repo_analyzer" for plugin in plugins.json())
    assert providers.status_code == 200
    assert {"cloud", "local"}.issubset({provider["mode"] for provider in providers.json()})
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
