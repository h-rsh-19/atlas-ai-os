# ruff: noqa: F401
from __future__ import annotations

import json
import re
import sqlite3
import time
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from atlas_api.core.config import get_settings
from atlas_api.schemas import (
    ApprovalAction,
    ApprovalActionCreate,
    ArtifactRecord,
    Citation,
    CodeAnalysisResult,
    CodeGraph,
    CodeRiskItem,
    CodeRiskReport,
    CodeSymbol,
    DashboardSummary,
    DecisionCreate,
    DecisionEntry,
    DecisionUpdate,
    DemoFlowStatus,
    DemoFlowStep,
    EmbeddingReindexResponse,
    EvaluationPrompt,
    EvaluationRun,
    ForgetMemoryResponse,
    JournalEntry,
    JournalEntryCreate,
    JournalSummary,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    MemoryCreate,
    MemoryExport,
    MemoryItem,
    MemoryUpdate,
    ModelProvider,
    PluginManifest,
    PluginUpdate,
    PrivacySettings,
    PrivacySettingsUpdate,
    RedactionPreviewResponse,
    RepoFile,
    RepoProject,
    ResumeProfile,
    ResumeStructuredProfile,
    RetrievalHit,
    SelfEvaluationRequest,
    SelfEvaluationResponse,
    SimulationAnswerRequest,
    SimulationRun,
    SimulationStartRequest,
    SimulatorScenario,
    SkillTreeItem,
    SkillTreeResponse,
    SourceDocument,
    TimelineEvent,
    TraceRun,
    TraceStep,
    UserProfile,
    UserProfileUpdate,
    WorkflowDefinition,
    WorkflowRunDetail,
)
from atlas_api.services.chunking import chunk_text, summarize_text
from atlas_api.services.code_intelligence import analyze_repository
from atlas_api.services.embeddings import cosine_similarity
from atlas_api.services.llm import workflow_template
from atlas_api.services.resume_parser import StructuredResume
from atlas_api.services.store_shared import (
    artifact_dir as _artifact_dir,
)
from atlas_api.services.store_shared import (
    decode_json,
    encode_json,
    new_id,
    now,
)
from atlas_api.services.store_shared import (
    default_redaction_patterns as _default_redaction_patterns,
)
from atlas_api.services.store_shared import (
    dependency_filenames as _dependency_filenames,
)
from atlas_api.services.store_shared import (
    ignored_repo_path as _ignored_repo_path,
)
from atlas_api.services.store_shared import (
    is_text_path as _is_text_path,
)
from atlas_api.services.store_shared import (
    language_for_path as _language_for_path,
)
from atlas_api.services.store_shared import (
    skill_category as _skill_category,
)
from atlas_api.services.store_shared import (
    slug as _slug,
)
from atlas_api.services.store_shared import (
    strip_zip_root as _strip_zip_root,
)


class CodeService:
    def connect_github_repo(self, github_url: str) -> RepoProject:
        self.initialize()
        name = github_url.rstrip("/").split("/")[-1] or "github-repo"
        project_id = new_id("repo")
        timestamp = now().isoformat()
        readme = (
            "Remote GitHub URL connected. Upload a repository ZIP to extract source files "
            "in this local-first checkpoint."
        )
        file_tree = [
            RepoFile(
                path="README.md",
                kind="file",
                language="Markdown",
                size_bytes=len(readme),
                preview=readme,
            )
        ]
        summary = (
            f"{name} is connected from GitHub metadata. Full code intelligence is "
            "available after ZIP ingestion."
        )
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into repo_projects (
                    id, name, origin_type, origin_url, status, summary,
                    language_stats, readme, dependency_files, file_tree, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    "github",
                    github_url,
                    "connected",
                    summary,
                    encode_json({"Markdown": 1}),
                    readme,
                    encode_json([]),
                    encode_json([item.model_dump(mode="json") for item in file_tree]),
                    timestamp,
                ),
            )
            db.commit()
            row = db.execute("select * from repo_projects where id = ?", (project_id,)).fetchone()
        return self._repo_from_row(row)


    def ingest_repo_zip(self, filename: str, zip_bytes: bytes) -> RepoProject:
        self.initialize()
        project_id = new_id("repo")
        name = Path(filename).stem or "uploaded-repo"
        files: list[RepoFile] = []
        language_stats: dict[str, int] = {}
        dependency_files: list[str] = []
        readme: str | None = None

        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            for info in archive.infolist():
                if info.is_dir() or info.file_size > 300_000:
                    continue
                path = _strip_zip_root(info.filename)
                if not path or _ignored_repo_path(path):
                    continue
                language = _language_for_path(path)
                if language:
                    language_stats[language] = language_stats.get(language, 0) + 1
                preview = None
                if _is_text_path(path):
                    raw = archive.read(info)
                    preview = raw.decode("utf-8", errors="ignore")[:1200]
                    if Path(path).name.lower() == "readme.md" and readme is None:
                        readme = preview
                if Path(path).name.lower() in _dependency_filenames():
                    dependency_files.append(path)
                files.append(
                    RepoFile(
                        path=path,
                        kind="file",
                        language=language,
                        size_bytes=info.file_size,
                        preview=preview,
                    )
                )

        summary = self._repo_summary(name, files, language_stats, dependency_files, readme)
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into repo_projects (
                    id, name, origin_type, origin_url, status, summary,
                    language_stats, readme, dependency_files, file_tree, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    "zip",
                    filename,
                    "indexed",
                    summary,
                    encode_json(language_stats),
                    readme,
                    encode_json(dependency_files),
                    encode_json([item.model_dump(mode="json") for item in files[:500]]),
                    timestamp,
                ),
            )
            source_id = self._insert_source(
                db,
                title=f"Repository {name}",
                source_type="project",
                uri=f"repo://{project_id}",
                raw_text=summary,
                metadata={"project_id": project_id, "filename": filename},
            )
            self._insert_memory(
                db,
                source_id=source_id,
                memory_type="project",
                title=f"Repository summary: {name}",
                content=summary,
                tags=["repo", "project", *list(language_stats.keys())[:4]],
                importance=0.8,
                metadata={"project_id": project_id},
            )
            db.commit()
            row = db.execute("select * from repo_projects where id = ?", (project_id,)).fetchone()
        return self._repo_from_row(row)


    def list_repos(self) -> list[RepoProject]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from repo_projects order by datetime(created_at) desc"
            ).fetchall()
        return [self._repo_from_row(row) for row in rows]


    def get_repo(self, project_id: str) -> RepoProject | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from repo_projects where id = ?", (project_id,)).fetchone()
        return self._repo_from_row(row) if row else None


    def analyze_codebase(self, project_id: str) -> CodeAnalysisResult | None:
        self.initialize()
        project = self.get_repo(project_id)
        if not project:
            return None

        symbols, graph, risk_report = analyze_repository(project)
        with self._lock, self._connect() as db:
            db.execute("delete from code_symbols where project_id = ?", (project_id,))
            for symbol in symbols:
                db.execute(
                    """
                    insert into code_symbols (
                        id, project_id, name, kind, file_path, language, line_start,
                        line_end, signature, evidence, metadata, created_at
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol.id,
                        symbol.project_id,
                        symbol.name,
                        symbol.kind,
                        symbol.file_path,
                        symbol.language,
                        symbol.line_start,
                        symbol.line_end,
                        symbol.signature,
                        symbol.evidence,
                        encode_json(symbol.metadata),
                        symbol.created_at.isoformat(),
                    ),
                )
            db.execute(
                """
                insert into code_graphs (
                    project_id, generated_at, parser_provider, nodes, edges, metrics
                )
                values (?, ?, ?, ?, ?, ?)
                on conflict(project_id) do update set
                    generated_at = excluded.generated_at,
                    parser_provider = excluded.parser_provider,
                    nodes = excluded.nodes,
                    edges = excluded.edges,
                    metrics = excluded.metrics
                """,
                (
                    graph.project_id,
                    graph.generated_at.isoformat(),
                    graph.parser_provider,
                    encode_json([node.model_dump(mode="json") for node in graph.nodes]),
                    encode_json([edge.model_dump(mode="json") for edge in graph.edges]),
                    encode_json(graph.metrics),
                ),
            )
            db.execute(
                """
                insert into code_risk_reports (
                    project_id, generated_at, summary, risks, metrics
                )
                values (?, ?, ?, ?, ?)
                on conflict(project_id) do update set
                    generated_at = excluded.generated_at,
                    summary = excluded.summary,
                    risks = excluded.risks,
                    metrics = excluded.metrics
                """,
                (
                    risk_report.project_id,
                    risk_report.generated_at.isoformat(),
                    risk_report.summary,
                    encode_json([risk.model_dump(mode="json") for risk in risk_report.risks]),
                    encode_json(risk_report.metrics),
                ),
            )
            db.execute(
                "update repo_projects set status = ? where id = ?",
                ("analyzed", project_id),
            )
            db.commit()

        refreshed = self.get_repo(project_id) or project
        return CodeAnalysisResult(
            project=refreshed,
            symbols=symbols,
            graph=graph,
            risk_report=risk_report,
        )


    def list_code_symbols(
        self,
        *,
        project_id: str | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[CodeSymbol]:
        self.initialize()
        clauses: list[str] = []
        values: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            values.append(project_id)
        if query:
            clauses.append("(lower(name) like ? or lower(file_path) like ? or lower(kind) like ?)")
            pattern = f"%{query.lower()}%"
            values.extend([pattern, pattern, pattern])
        where = " where " + " and ".join(clauses) if clauses else ""
        values.append(limit)
        with self._connect() as db:
            rows = db.execute(
                f"""
                select * from code_symbols{where}
                order by file_path asc, line_start asc
                limit ?
                """,
                tuple(values),
            ).fetchall()
        return [self._code_symbol_from_row(row) for row in rows]


    def get_code_graph(self, project_id: str) -> CodeGraph | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "select * from code_graphs where project_id = ?",
                (project_id,),
            ).fetchone()
        return self._code_graph_from_row(row) if row else None


    def get_code_risks(self, project_id: str) -> CodeRiskReport | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "select * from code_risk_reports where project_id = ?",
                (project_id,),
            ).fetchone()
        return self._code_risk_report_from_row(row) if row else None


