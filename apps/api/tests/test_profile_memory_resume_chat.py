from fastapi.testclient import TestClient

from atlas_api.main import app

client = TestClient(app)


def test_profile_can_be_created_and_retrieved() -> None:
    payload = {
        "name": "Atlas Builder",
        "role": "AI Product Engineer",
        "current_goals": ["Build Atlas with memory and traceability"],
        "target_roles": ["AI Engineer", "Backend Engineer"],
        "skills": ["Python", "FastAPI", "React"],
        "weaknesses": ["Distributed systems interview depth"],
        "preferred_tech_stack": ["Next.js", "FastAPI", "PostgreSQL"],
        "learning_priorities": ["pgvector retrieval", "agent evaluation"],
    }

    update_response = client.put("/api/profile", json=payload)
    get_response = client.get("/api/profile")

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Atlas Builder"
    assert "pgvector retrieval" in get_response.json()["learning_priorities"]


def test_memory_crud_and_retrieval() -> None:
    create_response = client.post(
        "/api/memory",
        json={
            "source_title": "Daily learning note",
            "source_type": "note",
            "memory_type": "learning",
            "title": "Retrieval practice",
            "content": "Focus on pgvector retrieval, citations, and grounded chat for Atlas.",
            "tags": ["learning", "retrieval"],
            "importance": 0.8,
        },
    )
    assert create_response.status_code == 201
    memory = create_response.json()

    search_response = client.post(
        "/api/retrieval/query",
        json={"query": "What should I learn about retrieval?", "top_k": 5},
    )
    assert search_response.status_code == 200
    assert any(hit["memory_id"] == memory["id"] for hit in search_response.json()["hits"])

    update_response = client.put(
        f"/api/memory/{memory['id']}",
        json={"importance": 0.9, "tags": ["learning", "retrieval", "priority"]},
    )
    assert update_response.status_code == 200
    assert "priority" in update_response.json()["tags"]

    delete_response = client.delete(f"/api/memory/{memory['id']}")
    assert delete_response.status_code == 204


def test_resume_pdf_upload_parses_sections_and_creates_memories() -> None:
    pdf = _minimal_pdf(
        [
            "Education",
            "BS Computer Science",
            "Projects",
            "Atlas personal AI OS with memory retrieval approvals and traces",
            "Skills",
            "Python, FastAPI, React, PostgreSQL",
            "Achievements",
            "Built recruiter-ready AI engineering project",
        ]
    )

    response = client.post(
        "/api/resume/upload?filename=atlas-resume.pdf",
        content=pdf,
        headers={"content-type": "application/pdf"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "BS Computer Science" in body["resume"]["structured"]["education"]
    assert "Python" in body["resume"]["structured"]["skills"]
    assert body["created_memories"]


def test_chat_uses_stored_context_and_returns_citations() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "What should I learn next?", "top_k": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert "learning focus" in body["answer"].lower()
    assert body["citations"]
    assert body["trace_id"]


def test_traces_capture_chat_evidence_and_steps() -> None:
    client.post("/api/chat", json={"message": "Generate interview pitch from my resume."})

    response = client.get("/api/traces")

    assert response.status_code == 200
    traces = response.json()
    assert traces
    chat_trace = next(trace for trace in traces if trace["prompt_version"] == "grounded-chat:v2")
    assert chat_trace["retrieved_memories"]
    assert chat_trace["steps"]


def test_workflow_engine_runs_named_workflow_with_trace() -> None:
    response = client.post(
        "/api/workflows/run",
        json={
            "workflow_name": "generate_resume_bullets",
            "inputs": {"target_role": "AI Product Engineer", "project": "Atlas"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["trace_id"]
    assert "bullets" in body["outputs"]
    assert body["outputs"]["_provider"]
    assert body["steps"][-1]["name"] == "record_trace"


def test_journal_entries_create_memory_and_summary() -> None:
    create_response = client.post(
        "/api/journal",
        json={
            "built": "Added project journal and career workflow generation.",
            "problems": "Needed grounded outputs from logs.",
            "decisions": "Store journal entries as daily log memories.",
            "skills_used": ["FastAPI", "Product thinking"],
            "next_tasks": ["Ingest repository ZIP"],
        },
    )
    summary_response = client.get("/api/journal/summary")

    assert create_response.status_code == 201
    assert summary_response.status_code == 200
    assert summary_response.json()["resume_bullets"]
    assert summary_response.json()["interview_stories"]


def test_repo_zip_ingestion_extracts_tree_and_summary() -> None:
    archive = _minimal_zip(
        {
            "atlas/README.md": "# Atlas\nPersonal AI OS",
            "atlas/package.json": "{\"dependencies\":{\"next\":\"16.2.9\"}}",
            "atlas/apps/api/main.py": "print('atlas')",
            "atlas/apps/web/page.tsx": "export default function Page() { return null }",
        }
    )

    response = client.post(
        "/api/projects/zip?filename=atlas.zip",
        content=archive,
        headers={"content-type": "application/zip"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_tree"]
    assert body["language_stats"]["Python"] == 1
    assert "package.json" in body["dependency_files"]


def _minimal_pdf(lines: list[str]) -> bytes:
    text_ops = " ".join(f"({line}) Tj" for line in lines)
    stream = f"BT /F1 12 Tf 72 720 Td {text_ops} ET"
    return f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length {len(stream)} >>
stream
{stream}
endstream
endobj
trailer
<< /Root 1 0 R >>
%%EOF
""".encode()


def _minimal_zip(files: dict[str, str]) -> bytes:
    from io import BytesIO
    from zipfile import ZIP_DEFLATED, ZipFile

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()
