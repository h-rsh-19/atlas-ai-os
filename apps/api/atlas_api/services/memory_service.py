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


class MemoryService:
    def create_source(
        self,
        *,
        title: str,
        source_type: str,
        uri: str | None,
        raw_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> SourceDocument:
        self.initialize()
        with self._lock, self._connect() as db:
            source_id = self._insert_source(
                db,
                title=title,
                source_type=source_type,
                uri=uri,
                raw_text=raw_text,
                metadata=metadata or {},
            )
            db.commit()
            row = db.execute("select * from source_documents where id = ?", (source_id,)).fetchone()
        return self._source_from_row(row)


    def create_memory(self, payload: MemoryCreate, *, source_id: str | None = None) -> MemoryItem:
        self.initialize()
        with self._lock, self._connect() as db:
            if not source_id:
                source_id = self._insert_source(
                    db,
                    title=payload.source_title,
                    source_type=payload.source_type,
                    uri=f"memory://{payload.source_type}/{uuid4().hex[:8]}",
                    raw_text=payload.content,
                    metadata=payload.metadata,
                )
            memory_id = self._insert_memory(
                db,
                source_id=source_id,
                memory_type=payload.memory_type,
                title=payload.title or payload.source_title,
                content=payload.content,
                tags=payload.tags,
                importance=payload.importance,
                metadata=payload.metadata,
            )
            db.commit()
            row = self._memory_row(db, memory_id)
        return self._memory_from_row(row)


    def list_memories(self) -> list[MemoryItem]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                """
                select memories.*, source_documents.title as source_title,
                       source_documents.source_type as source_type,
                       source_documents.uri as source_uri
                from memories
                join source_documents on source_documents.id = memories.source_id
                order by datetime(memories.updated_at) desc
                """
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]


    def get_memory(self, memory_id: str) -> MemoryItem | None:
        self.initialize()
        with self._connect() as db:
            row = self._memory_row(db, memory_id)
        return self._memory_from_row(row) if row else None


    def update_memory(self, memory_id: str, payload: MemoryUpdate) -> MemoryItem | None:
        self.initialize()
        current = self.get_memory(memory_id)
        if not current:
            return None

        title = (
            payload.title
            if payload.title is not None
            else current.title or current.source_title
        )
        content = (
            payload.content
            if payload.content is not None
            else current.content or current.summary
        )
        summary = payload.summary if payload.summary is not None else summarize_text(content)
        tags = payload.tags if payload.tags is not None else current.tags
        importance = payload.importance if payload.importance is not None else current.importance
        metadata = payload.metadata if payload.metadata is not None else current.metadata
        embedding_result = self.embedding_provider.embed(f"{title}\n{content}")
        embedding = embedding_result.vector
        metadata = {
            **metadata,
            "_embedding": embedding,
            "_embedding_provider": embedding_result.provider,
            "_embedding_model": embedding_result.model,
            "_embedding_dimensions": embedding_result.dimensions,
        }
        timestamp = now().isoformat()

        with self._lock, self._connect() as db:
            db.execute(
                """
                update memories
                set title = ?, content = ?, summary = ?, tags = ?, importance = ?,
                    metadata = ?, embedding = ?, updated_at = ?
                where id = ?
                """,
                (
                    title,
                    content,
                    summary,
                    encode_json(tags),
                    importance,
                    encode_json(metadata),
                    encode_json(embedding),
                    timestamp,
                    memory_id,
                ),
            )
            db.commit()
            row = self._memory_row(db, memory_id)
        return self._memory_from_row(row) if row else None


    def delete_memory(self, memory_id: str) -> bool:
        self.initialize()
        with self._lock, self._connect() as db:
            result = db.execute("delete from memories where id = ?", (memory_id,))
            db.commit()
        return result.rowcount > 0


    def search_memories(
        self,
        query: str,
        *,
        top_k: int,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[RetrievalHit]:
        self.initialize()
        query_embedding = self.embedding_provider.embed(query).vector
        memory_types = memory_types or []
        required_tags = {tag.lower() for tag in tags or []}

        hits: list[RetrievalHit] = []
        for memory in self.list_memories():
            if memory_types and memory.memory_type not in memory_types:
                continue
            memory_tags = {tag.lower() for tag in memory.tags}
            if required_tags and not required_tags.intersection(memory_tags):
                continue
            embedding = memory.metadata.get("_embedding")
            if not isinstance(embedding, list) or len(embedding) != len(query_embedding):
                embedding = self.embedding_provider.embed(
                    f"{memory.title}\n{memory.content}",
                ).vector
            vector_score = cosine_similarity(query_embedding, embedding)
            keyword_score = self._keyword_score(query, f"{memory.title} {memory.content}")
            score = round(
                (0.72 * vector_score)
                + (0.28 * keyword_score)
                + (memory.importance * 0.05),
                4,
            )
            hits.append(
                RetrievalHit(
                    memory_id=memory.id,
                    title=memory.title or memory.source_title,
                    memory_type=memory.memory_type,
                    content=memory.content or memory.summary,
                    summary=memory.summary,
                    score=score,
                    tags=memory.tags,
                    citations=memory.citations,
                )
            )

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]


    def reindex_embeddings(self) -> EmbeddingReindexResponse:
        self.initialize()
        reindexed_count = 0
        last_provider = self.embedding_provider.id
        last_model = self.embedding_provider.model
        last_dimensions = self.embedding_dimensions
        with self._lock, self._connect() as db:
            rows = db.execute("select * from memories order by datetime(created_at)").fetchall()
            for row in rows:
                title = row["title"] or ""
                content = row["content"] or row["summary"] or ""
                metadata = decode_json(row["metadata"], {})
                embedding_result = self.embedding_provider.embed(f"{title}\n{content}")
                metadata["_embedding"] = embedding_result.vector
                metadata["_embedding_provider"] = embedding_result.provider
                metadata["_embedding_model"] = embedding_result.model
                metadata["_embedding_dimensions"] = embedding_result.dimensions
                db.execute(
                    """
                    update memories
                    set metadata = ?, embedding = ?, updated_at = ?
                    where id = ?
                    """,
                    (
                        encode_json(metadata),
                        encode_json(embedding_result.vector),
                        now().isoformat(),
                        row["id"],
                    ),
                )
                reindexed_count += 1
                last_provider = embedding_result.provider
                last_model = embedding_result.model
                last_dimensions = embedding_result.dimensions
            db.commit()
        return EmbeddingReindexResponse(
            reindexed_count=reindexed_count,
            provider=last_provider,
            model=last_model,
            dimensions=last_dimensions,
        )


    def store_resume(
        self,
        *,
        filename: str,
        raw_text: str,
        structured: StructuredResume,
    ) -> tuple[ResumeProfile, list[MemoryItem]]:
        self.initialize()
        with self._lock, self._connect() as db:
            source_id = self._insert_source(
                db,
                title=filename,
                source_type="resume",
                uri=f"resume://{filename}",
                raw_text=raw_text,
                metadata={"filename": filename, "parser": "atlas-local"},
            )
            resume_id = new_id("resume")
            timestamp = now().isoformat()
            db.execute(
                """
                insert into resume_profiles (
                    id, source_id, filename, raw_text, structured, created_at
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    resume_id,
                    source_id,
                    filename,
                    raw_text,
                    encode_json(structured.as_dict()),
                    timestamp,
                ),
            )
            memory_ids = self._insert_resume_memories(db, source_id, structured, raw_text)
            db.commit()
            resume_row = db.execute(
                "select * from resume_profiles where id = ?",
                (resume_id,),
            ).fetchone()
            memory_rows = [self._memory_row(db, memory_id) for memory_id in memory_ids]

        return self._resume_from_row(resume_row), [
            self._memory_from_row(row) for row in memory_rows if row is not None
        ]


    def latest_resume(self) -> ResumeProfile | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "select * from resume_profiles order by datetime(created_at) desc limit 1"
            ).fetchone()
        return self._resume_from_row(row) if row else None


