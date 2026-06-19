from __future__ import annotations

from datetime import UTC, datetime

from atlas_api.schemas import (
    LabProofArtifact,
    LabsOverview,
    LabTrack,
    TinyDatabaseDemo,
)
from atlas_api.services.tiny_database import TinyAtlasDatabase


def labs_overview() -> LabsOverview:
    tiny_demo = run_tiny_database_demo()
    return LabsOverview(
        generated_at=datetime.now(UTC),
        tracks=[
            LabTrack(
                id="tiny_database_from_scratch",
                title="Tiny Database From Scratch",
                status="kernel shipped",
                resume_signal=(
                    "Systems fundamentals, storage internals, indexing, "
                    "and local-first design."
                ),
                implementation_level="Working learning kernel used by the Labs API and tests.",
                shipped=[
                    "Schema creation with primary-key validation.",
                    "Append-only operation log for traceable writes.",
                    "Point reads, scans, equality filters, updates, and deletes.",
                    "Explain output that exposes tables, rows, WAL entries, and index type.",
                ],
                next_steps=[
                    "Persist the WAL to a local file and replay it on startup.",
                    "Add secondary indexes and range scans.",
                    "Benchmark point reads versus full scans on seeded local data.",
                ],
                proof_artifacts=[
                    LabProofArtifact(
                        title="TinyAtlasDatabase",
                        kind="source",
                        path="apps/api/atlas_api/services/tiny_database.py",
                        evidence=(
                            "Local database kernel implemented without external "
                            "database libraries."
                        ),
                    ),
                    LabProofArtifact(
                        title="Tiny database tests",
                        kind="test",
                        path="apps/api/tests/test_labs_and_tiny_database.py",
                        evidence="CRUD, schema validation, and Labs API behavior are covered.",
                    ),
                ],
            ),
            LabTrack(
                id="local_code_intelligence_engine",
                title="Local Code Intelligence Engine",
                status="active product surface",
                resume_signal=(
                    "AST parsing, symbol extraction, dependency graphs, "
                    "and code-risk scoring."
                ),
                implementation_level=(
                    "Deterministic analyzer integrated with repository uploads "
                    "and UI graphs."
                ),
                shipped=[
                    "Python AST extraction for functions, classes, routes, imports, and calls.",
                    (
                        "TypeScript/JavaScript heuristic extraction for functions, "
                        "components, routes, and imports."
                    ),
                    (
                        "Route map, test coverage map, dependency hotspot ranking, "
                        "and refactor priority metrics."
                    ),
                    (
                        "Risk report with README, TODO, missing-test, large-file, "
                        "dependency, and cycle evidence."
                    ),
                ],
                next_steps=[
                    "Adopt tree-sitter grammars for deeper TypeScript and Python parsing.",
                    "Add diff-aware PR review mode.",
                    "Generate architecture diagrams directly from the stored graph.",
                ],
                proof_artifacts=[
                    LabProofArtifact(
                        title="Code intelligence analyzer",
                        kind="source",
                        path="apps/api/atlas_api/services/code_intelligence.py",
                        evidence=(
                            "Repo analysis returns symbols, graph metrics, "
                            "route maps, and risk evidence."
                        ),
                    ),
                    LabProofArtifact(
                        title="Code intelligence UI",
                        kind="ui",
                        path="apps/web/app/code/page.tsx",
                        evidence=(
                            "Graph, searchable symbols, and risk reports are "
                            "visible in the product."
                        ),
                    ),
                ],
            ),
            LabTrack(
                id="end_to_end_ml_platform_lite",
                title="End-To-End ML Platform Lite",
                status="blueprint integrated",
                resume_signal=(
                    "ML systems thinking: data, evaluation, provider policy, "
                    "traceability, and deployment."
                ),
                implementation_level=(
                    "Atlas maps the platform loop through evals, provider health, "
                    "traces, and artifacts."
                ),
                shipped=[
                    (
                        "Evaluation suite for retrieval, citation quality, "
                        "hallucination resistance, and workflows."
                    ),
                    (
                        "Provider health checks for deterministic, OpenAI, "
                        "Ollama, vLLM, and embeddings."
                    ),
                    (
                        "Trace records that capture inputs, evidence, prompt versions, "
                        "model state, latency, and errors."
                    ),
                    "Approval-gated artifact generation for recruiter/demo outputs.",
                ],
                next_steps=[
                    "Add dataset registry and versioned eval datasets.",
                    "Add model-run cost tracking and fallback policy tests.",
                    (
                        "Add a local training/evaluation worker for small classifier "
                        "or ranking experiments."
                    ),
                ],
                proof_artifacts=[
                    LabProofArtifact(
                        title="Evaluation strategy",
                        kind="doc",
                        path="docs/evaluation-strategy.md",
                        evidence="Golden prompts and quality rubrics define the evaluation loop.",
                    ),
                    LabProofArtifact(
                        title="Provider health",
                        kind="ui",
                        path="apps/web/app/providers/page.tsx",
                        evidence="Runtime model and embedding status is visible instead of hidden.",
                    ),
                ],
            ),
        ],
        tiny_database_demo=tiny_demo,
        portfolio_pitch=(
            "Atlas now reads as a personal AI OS plus a systems portfolio: local memory, "
            "traceable agents, approval-gated tools, code intelligence, a tiny database lab, "
            "and an ML-platform evaluation loop."
        ),
        next_best_iteration=(
            "Persist TinyAtlasDatabase WAL files, add Alembic migrations, and convert demo "
            "flows into resumable workflow checkpoints."
        ),
    )


def run_tiny_database_demo() -> TinyDatabaseDemo:
    db = TinyAtlasDatabase()
    db.create_table("memories", ["id", "kind", "title", "importance"])
    db.insert(
        "memories",
        {
            "id": "mem_001",
            "kind": "project",
            "title": "Atlas local code intelligence",
            "importance": 0.91,
        },
    )
    db.insert(
        "memories",
        {
            "id": "mem_002",
            "kind": "learning",
            "title": "Tiny database storage kernel",
            "importance": 0.84,
        },
    )
    db.update("memories", "mem_002", {"importance": 0.89})
    result = db.where("memories", kind="learning")[0]
    explain = db.explain()
    return TinyDatabaseDemo(
        engine="TinyAtlasDatabase",
        operations=[
            "create_table(memories)",
            "insert(project memory)",
            "insert(learning memory)",
            "update(learning importance)",
            "where(kind=learning)",
        ],
        row_count=explain["tables"]["memories"]["rows"],
        query_result=result,
        explanation=(
            "The lab demonstrates database internals with a schema registry, hash-map "
            "primary-key index, append-only operation log, and deterministic query path."
        ),
    )
