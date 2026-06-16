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


class PrivacyService:
    def get_privacy_settings(self) -> PrivacySettings:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from privacy_settings where id = ?", ("default",)).fetchone()
        return self._privacy_from_row(row)


    def update_privacy_settings(self, payload: PrivacySettingsUpdate) -> PrivacySettings:
        self.initialize()
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into privacy_settings (
                    id, allowed_folders, blocked_folders, redaction_patterns,
                    local_only, memory_export_enabled, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    allowed_folders = excluded.allowed_folders,
                    blocked_folders = excluded.blocked_folders,
                    redaction_patterns = excluded.redaction_patterns,
                    local_only = excluded.local_only,
                    memory_export_enabled = excluded.memory_export_enabled,
                    updated_at = excluded.updated_at
                """,
                (
                    "default",
                    encode_json(payload.allowed_folders),
                    encode_json(payload.blocked_folders),
                    encode_json(payload.redaction_patterns),
                    int(payload.local_only),
                    int(payload.memory_export_enabled),
                    timestamp,
                ),
            )
            db.commit()
        return self.get_privacy_settings()


    def redact_text(self, text: str) -> RedactionPreviewResponse:
        settings = self.get_privacy_settings()
        replacements: list[dict[str, str]] = []
        redacted = text
        for index, pattern in enumerate(settings.redaction_patterns):
            try:
                matches = re.findall(pattern, redacted)
                if matches:
                    token = f"[REDACTED_{index + 1}]"
                    redacted = re.sub(pattern, token, redacted)
                    replacements.append({"pattern": pattern, "replacement": token})
            except re.error:
                replacements.append({"pattern": pattern, "replacement": "[INVALID_PATTERN]"})
        return RedactionPreviewResponse(redacted_text=redacted, replacements=replacements)


    def export_memory(self, *, redacted: bool = True) -> MemoryExport:
        settings = self.get_privacy_settings()
        if not settings.memory_export_enabled:
            return MemoryExport(
                exported_at=now(),
                redacted=redacted,
                memories=[],
                source_count=0,
            )
        memories = self.list_memories()
        if redacted:
            redacted_memories: list[MemoryItem] = []
            for memory in memories:
                clone = memory.model_copy(deep=True)
                if clone.content:
                    clone.content = self.redact_text(clone.content).redacted_text
                clone.summary = self.redact_text(clone.summary).redacted_text
                redacted_memories.append(clone)
            memories = redacted_memories
        source_ids = {memory.source_id for memory in memories if memory.source_id}
        return MemoryExport(
            exported_at=now(),
            redacted=redacted,
            memories=memories,
            source_count=len(source_ids),
        )


    def forget_memory(
        self,
        *,
        memory_id: str | None = None,
        query: str | None = None,
    ) -> ForgetMemoryResponse:
        self.initialize()
        candidates: list[MemoryItem] = []
        if memory_id:
            memory = self.get_memory(memory_id)
            if memory:
                candidates.append(memory)
        elif query:
            query_lower = query.lower()
            candidates = [
                memory
                for memory in self.list_memories()
                if query_lower in (memory.title or "").lower()
                or query_lower in (memory.content or memory.summary).lower()
            ][:20]

        deleted_ids: list[str] = []
        with self._lock, self._connect() as db:
            for memory in candidates:
                result = db.execute("delete from memories where id = ?", (memory.id,))
                if result.rowcount:
                    deleted_ids.append(memory.id)
            db.commit()
        trace = self.create_trace(
            interaction_type="privacy:forget_memory",
            user_input=query or memory_id or "",
            retrieved_memories=[],
            prompt_version="privacy-v1",
            model_used="atlas-local-privacy-v1",
            tool_calls=[{"tool": "memory.delete", "count": len(deleted_ids)}],
            generated_output={"deleted_memory_ids": deleted_ids},
            latency_ms=3,
            confidence=1.0,
            assumptions=["User-initiated forget action deletes matching memory rows."],
        )
        return ForgetMemoryResponse(
            deleted_count=len(deleted_ids),
            deleted_memory_ids=deleted_ids,
            trace_id=trace.id,
        )


