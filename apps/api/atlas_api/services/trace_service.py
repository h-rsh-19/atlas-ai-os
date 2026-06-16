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


class TraceService:
    def create_trace(
        self,
        *,
        interaction_type: str,
        user_input: str,
        retrieved_memories: list[RetrievalHit],
        prompt_version: str,
        model_used: str,
        tool_calls: list[dict[str, Any]],
        generated_output: dict[str, Any],
        latency_ms: int,
        errors: list[str] | None = None,
        confidence: float = 0.75,
        assumptions: list[str] | None = None,
        steps: list[TraceStep] | None = None,
        workflow_run_id: str | None = None,
    ) -> TraceRun:
        self.initialize()
        trace_id = new_id("trace")
        timestamp = now().isoformat()
        trace_steps = steps or []
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into trace_runs (
                    id, interaction_type, user_input, retrieved_memories, prompt_version,
                    model_used, tool_calls, generated_output, latency_ms, errors,
                    confidence, assumptions, steps, workflow_run_id, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    interaction_type,
                    user_input,
                    encode_json([hit.model_dump(mode="json") for hit in retrieved_memories]),
                    prompt_version,
                    model_used,
                    encode_json(tool_calls),
                    encode_json(generated_output),
                    latency_ms,
                    encode_json(errors or []),
                    confidence,
                    encode_json(assumptions or []),
                    encode_json([step.model_dump(mode="json") for step in trace_steps]),
                    workflow_run_id,
                    timestamp,
                ),
            )
            db.commit()
            row = db.execute("select * from trace_runs where id = ?", (trace_id,)).fetchone()
        return self._trace_from_row(row)


    def list_traces(self) -> list[TraceRun]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from trace_runs order by datetime(created_at) desc"
            ).fetchall()
        return [self._trace_from_row(row) for row in rows]


    def get_trace(self, trace_id: str) -> TraceRun | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from trace_runs where id = ?", (trace_id,)).fetchone()
        return self._trace_from_row(row) if row else None


