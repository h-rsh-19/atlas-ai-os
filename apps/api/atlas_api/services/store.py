from __future__ import annotations

import json
import re
import sqlite3
import threading
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
from atlas_api.services.embeddings import cosine_similarity, embed_text
from atlas_api.services.resume_parser import StructuredResume


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


class AtlasStore:
    def __init__(self, path: str, embedding_dimensions: int) -> None:
        self.path = path
        self.embedding_dimensions = embedding_dimensions
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as db:
                db.executescript(
                    """
                    create table if not exists user_profiles (
                        id text primary key,
                        name text not null,
                        role text not null,
                        current_goals text not null,
                        target_roles text not null,
                        skills text not null,
                        weaknesses text not null,
                        preferred_tech_stack text not null,
                        learning_priorities text not null,
                        updated_at text not null
                    );

                    create table if not exists source_documents (
                        id text primary key,
                        title text not null,
                        source_type text not null,
                        uri text,
                        raw_text text,
                        metadata text not null,
                        created_at text not null
                    );

                    create table if not exists memories (
                        id text primary key,
                        source_id text not null,
                        memory_type text not null,
                        title text not null,
                        content text not null,
                        summary text not null,
                        tags text not null,
                        importance real not null,
                        source_references text not null,
                        metadata text not null,
                        embedding text not null,
                        created_at text not null,
                        updated_at text not null,
                        foreign key (source_id) references source_documents(id)
                    );

                    create table if not exists resume_profiles (
                        id text primary key,
                        source_id text not null,
                        filename text not null,
                        raw_text text not null,
                        structured text not null,
                        created_at text not null,
                        foreign key (source_id) references source_documents(id)
                    );

                    create table if not exists trace_runs (
                        id text primary key,
                        interaction_type text not null,
                        user_input text not null,
                        retrieved_memories text not null,
                        prompt_version text not null,
                        model_used text not null,
                        tool_calls text not null,
                        generated_output text not null,
                        latency_ms integer not null,
                        errors text not null,
                        confidence real not null,
                        assumptions text not null,
                        steps text not null,
                        workflow_run_id text,
                        created_at text not null
                    );

                    create table if not exists workflow_runs_local (
                        id text primary key,
                        workflow_name text not null,
                        status text not null,
                        inputs text not null,
                        outputs text not null,
                        steps text not null,
                        trace_id text,
                        created_at text not null,
                        updated_at text not null
                    );

                    create table if not exists journal_entries (
                        id text primary key,
                        built text not null,
                        problems text not null,
                        decisions text not null,
                        skills_used text not null,
                        next_tasks text not null,
                        entry_date text not null,
                        created_at text not null
                    );

                    create table if not exists repo_projects (
                        id text primary key,
                        name text not null,
                        origin_type text not null,
                        origin_url text,
                        status text not null,
                        summary text not null,
                        language_stats text not null,
                        readme text,
                        dependency_files text not null,
                        file_tree text not null,
                        created_at text not null
                    );

                    create table if not exists code_symbols (
                        id text primary key,
                        project_id text not null,
                        name text not null,
                        kind text not null,
                        file_path text not null,
                        language text,
                        line_start integer not null,
                        line_end integer not null,
                        signature text,
                        evidence text not null,
                        metadata text not null,
                        created_at text not null,
                        foreign key (project_id) references repo_projects(id)
                    );

                    create table if not exists code_graphs (
                        project_id text primary key,
                        generated_at text not null,
                        parser_provider text not null,
                        nodes text not null,
                        edges text not null,
                        metrics text not null,
                        foreign key (project_id) references repo_projects(id)
                    );

                    create table if not exists code_risk_reports (
                        project_id text primary key,
                        generated_at text not null,
                        summary text not null,
                        risks text not null,
                        metrics text not null,
                        foreign key (project_id) references repo_projects(id)
                    );

                    create table if not exists approval_actions (
                        id text primary key,
                        tool_name text not null,
                        title text not null,
                        status text not null,
                        risk_level text not null,
                        inputs text not null,
                        preview text not null,
                        result text not null,
                        artifact_path text,
                        trace_id text,
                        created_at text not null,
                        updated_at text not null
                    );

                    create table if not exists artifact_records (
                        id text primary key,
                        action_id text not null,
                        title text not null,
                        kind text not null,
                        path text not null,
                        content_preview text not null,
                        created_at text not null,
                        foreign key (action_id) references approval_actions(id)
                    );

                    create table if not exists eval_runs (
                        id text primary key,
                        status text not null,
                        generated_at text not null,
                        results text not null,
                        summary text not null,
                        trace_id text
                    );

                    create table if not exists privacy_settings (
                        id text primary key,
                        allowed_folders text not null,
                        blocked_folders text not null,
                        redaction_patterns text not null,
                        local_only integer not null,
                        memory_export_enabled integer not null,
                        updated_at text not null
                    );

                    create table if not exists decision_entries (
                        id text primary key,
                        title text not null,
                        decision text not null,
                        alternatives text not null,
                        tradeoffs text not null,
                        reason text not null,
                        result text,
                        tags text not null,
                        memory_id text,
                        created_at text not null,
                        updated_at text not null
                    );

                    create table if not exists simulation_runs (
                        id text primary key,
                        scenario_id text not null,
                        scenario_type text not null,
                        title text not null,
                        prompt text not null,
                        rubric text not null,
                        status text not null,
                        answer text,
                        evaluation text not null,
                        trace_id text,
                        created_at text not null,
                        updated_at text not null
                    );

                    create table if not exists plugin_registry (
                        id text primary key,
                        name text not null,
                        category text not null,
                        description text not null,
                        enabled integer not null,
                        permission_scopes text not null,
                        status text not null,
                        config text not null,
                        updated_at text not null
                    );

                    create index if not exists ix_memories_type on memories(memory_type);
                    create index if not exists ix_memories_source on memories(source_id);
                    create index if not exists ix_trace_runs_created on trace_runs(created_at);
                    create index if not exists ix_workflow_runs_created
                        on workflow_runs_local(created_at);
                    create index if not exists ix_journal_entries_date
                        on journal_entries(entry_date);
                    create index if not exists ix_code_symbols_project
                        on code_symbols(project_id);
                    create index if not exists ix_code_symbols_name
                        on code_symbols(name);
                    create index if not exists ix_approval_actions_status
                        on approval_actions(status);
                    create index if not exists ix_decision_entries_created
                        on decision_entries(created_at);
                    create index if not exists ix_simulation_runs_created
                        on simulation_runs(created_at);
                    """
                )
                self._ensure_profile(db)
                self._ensure_seed_memory(db)
                self._ensure_privacy_settings(db)
                self._ensure_plugins(db)
                db.commit()
            self._initialized = True

    def get_profile(self) -> UserProfile:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from user_profiles where id = ?", ("default",)).fetchone()
        return self._profile_from_row(row)

    def update_profile(self, payload: UserProfileUpdate) -> UserProfile:
        self.initialize()
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into user_profiles (
                    id, name, role, current_goals, target_roles, skills, weaknesses,
                    preferred_tech_stack, learning_priorities, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    name = excluded.name,
                    role = excluded.role,
                    current_goals = excluded.current_goals,
                    target_roles = excluded.target_roles,
                    skills = excluded.skills,
                    weaknesses = excluded.weaknesses,
                    preferred_tech_stack = excluded.preferred_tech_stack,
                    learning_priorities = excluded.learning_priorities,
                    updated_at = excluded.updated_at
                """,
                (
                    "default",
                    payload.name,
                    payload.role,
                    encode_json(payload.current_goals),
                    encode_json(payload.target_roles),
                    encode_json(payload.skills),
                    encode_json(payload.weaknesses),
                    encode_json(payload.preferred_tech_stack),
                    encode_json(payload.learning_priorities),
                    timestamp,
                ),
            )
            source_id = self._upsert_source(
                db,
                title="Personal Profile",
                source_type="profile",
                uri="profile://default",
                raw_text=self._profile_text(payload),
                metadata={"owner": "default"},
            )
            self._upsert_profile_memory(db, source_id, payload)
            db.commit()
        return self.get_profile()

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
        embedding = embed_text(f"{title}\n{content}", self.embedding_dimensions)
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
        query_embedding = embed_text(query, self.embedding_dimensions)
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
            if not isinstance(embedding, list):
                embedding = embed_text(
                    f"{memory.title}\n{memory.content}",
                    self.embedding_dimensions,
                )
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

    def workflow_definitions(self) -> list[WorkflowDefinition]:
        common_steps = ["load_profile", "retrieve_memory", "compose_output", "record_trace"]
        return [
            WorkflowDefinition(
                name="plan_my_day",
                description="Create a focused daily plan from goals, memory, and next tasks.",
                category="planning",
                required_inputs=["focus"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="plan_my_week",
                description="Turn goals and journal entries into a weekly execution plan.",
                category="planning",
                required_inputs=["theme"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="create_project_journal",
                description="Convert progress input into a structured project journal entry.",
                category="journal",
                required_inputs=["built"],
                steps=["parse_log", "save_journal", "create_memory", "record_trace"],
            ),
            WorkflowDefinition(
                name="generate_resume_bullets",
                description="Generate resume bullets from resume evidence, memory, and journals.",
                category="career",
                required_inputs=["target_role"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="prepare_interview_answer",
                description="Draft a specific interview answer grounded in project evidence.",
                category="career",
                required_inputs=["question"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="suggest_learning_plan",
                description="Suggest a learning plan from goals, weak areas, and project work.",
                category="learning",
                required_inputs=["time_horizon"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="resume_gap_analysis",
                description="Find gaps between current resume evidence and target roles.",
                category="career",
                required_inputs=["target_role"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="role_match_analysis",
                description="Score fit for a role using profile, resume, memory, and logs.",
                category="career",
                required_inputs=["role"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="project_to_resume_bullets",
                description="Turn project memories into recruiter-ready resume bullets.",
                category="career",
                required_inputs=["project"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="interview_story_generator",
                description="Create STAR-style interview stories from project journal evidence.",
                category="career",
                required_inputs=["competency"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="skill_growth_plan",
                description="Create a skill growth plan from weak areas and target roles.",
                category="career",
                required_inputs=["skill"],
                steps=common_steps,
            ),
            WorkflowDefinition(
                name="architecture_summary",
                description=(
                    "Summarize an indexed codebase using symbols, graph, "
                    "and file evidence."
                ),
                category="code",
                required_inputs=["project_id"],
                steps=["load_repo", "load_graph", "load_symbols", "compose_output", "record_trace"],
            ),
            WorkflowDefinition(
                name="onboarding_guide",
                description="Create an onboarding guide from repository structure and risks.",
                category="code",
                required_inputs=["project_id"],
                steps=["load_repo", "load_graph", "load_risks", "compose_output", "record_trace"],
            ),
            WorkflowDefinition(
                name="refactor_plan",
                description="Turn deterministic code risks into a practical refactor plan.",
                category="code",
                required_inputs=["project_id"],
                steps=["load_repo", "load_risks", "prioritize_changes", "record_trace"],
            ),
            WorkflowDefinition(
                name="test_plan",
                description="Generate a test plan from missing-test and hotspot evidence.",
                category="code",
                required_inputs=["project_id"],
                steps=["load_repo", "load_risks", "map_tests", "record_trace"],
            ),
            WorkflowDefinition(
                name="PR_review_draft",
                description="Draft a PR review using symbol graph and deterministic risk evidence.",
                category="code",
                required_inputs=["project_id"],
                steps=["load_repo", "load_graph", "load_risks", "compose_output", "record_trace"],
            ),
            WorkflowDefinition(
                name="bug_investigation_plan",
                description=(
                    "Create a bug investigation path from symbols, dependencies, "
                    "and risks."
                ),
                category="code",
                required_inputs=["project_id", "symptom"],
                steps=["load_repo", "search_symbols", "inspect_risks", "record_trace"],
            ),
        ]

    def list_workflow_runs(self) -> list[WorkflowRunDetail]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from workflow_runs_local order by datetime(created_at) desc"
            ).fetchall()
        return [self._workflow_from_row(row) for row in rows]

    def run_workflow(self, workflow_name: str, inputs: dict[str, Any]) -> WorkflowRunDetail:
        self.initialize()
        definition = next(
            (item for item in self.workflow_definitions() if item.name == workflow_name),
            None,
        )
        if not definition:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        started = time.perf_counter()
        run_id = new_id("wf")
        timestamp = now().isoformat()
        query = " ".join(str(value) for value in inputs.values()) or workflow_name
        hits = self.search_memories(query, top_k=5)
        profile = self.get_profile()
        journals = self.list_journal_entries(limit=5)
        steps: list[TraceStep] = []

        steps.append(
            TraceStep(
                name="load_profile",
                status="completed",
                output={"name": profile.name, "role": profile.role},
                latency_ms=4,
            )
        )
        steps.append(
            TraceStep(
                name="retrieve_memory",
                status="completed",
                input={"query": query},
                output={"hits": len(hits)},
                tool_calls=[{"tool": "memory.search", "top_k": 5}],
                latency_ms=11,
            )
        )

        outputs = self._workflow_output(workflow_name, inputs, profile, hits, journals)
        steps.append(
            TraceStep(
                name="compose_output",
                status="completed",
                output={"keys": list(outputs.keys())},
                latency_ms=7,
            )
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        assumptions = [
            "Local deterministic workflow engine used instead of external LLM.",
            "Outputs are grounded in current stored profile, memories, resume, and journals.",
        ]
        trace = self.create_trace(
            interaction_type=f"workflow:{workflow_name}",
            user_input=encode_json(inputs),
            retrieved_memories=hits,
            prompt_version="workflow-mvp-v1",
            model_used="atlas-deterministic-workflow-v1",
            tool_calls=[{"tool": "memory.search"}, {"tool": "journal.list"}],
            generated_output=outputs,
            latency_ms=latency_ms,
            confidence=0.78 if hits else 0.58,
            assumptions=assumptions,
            steps=steps,
            workflow_run_id=run_id,
        )
        steps.append(
            TraceStep(
                name="record_trace",
                status="completed",
                output={"trace_id": trace.id},
                latency_ms=3,
            )
        )

        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into workflow_runs_local (
                    id, workflow_name, status, inputs, outputs, steps,
                    trace_id, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    workflow_name,
                    "completed",
                    encode_json(inputs),
                    encode_json(outputs),
                    encode_json([step.model_dump(mode="json") for step in steps]),
                    trace.id,
                    timestamp,
                    now().isoformat(),
                ),
            )
            db.execute(
                "update trace_runs set workflow_run_id = ? where id = ?",
                (run_id, trace.id),
            )
            db.commit()
            row = db.execute(
                "select * from workflow_runs_local where id = ?",
                (run_id,),
            ).fetchone()
        return self._workflow_from_row(row)

    def create_journal_entry(self, payload: JournalEntryCreate) -> JournalEntry:
        self.initialize()
        entry_id = new_id("journal")
        entry_date = payload.entry_date or now().date().isoformat()
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into journal_entries (
                    id, built, problems, decisions, skills_used,
                    next_tasks, entry_date, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    payload.built,
                    payload.problems,
                    payload.decisions,
                    encode_json(payload.skills_used),
                    encode_json(payload.next_tasks),
                    entry_date,
                    timestamp,
                ),
            )
            source_id = self._insert_source(
                db,
                title=f"Journal {entry_date}",
                source_type="daily log",
                uri=f"journal://{entry_id}",
                raw_text=self._journal_text(payload),
                metadata={"entry_date": entry_date},
            )
            self._insert_memory(
                db,
                source_id=source_id,
                memory_type="daily log",
                title=f"Journal {entry_date}",
                content=self._journal_text(payload),
                tags=["journal", "daily log", *payload.skills_used],
                importance=0.75,
                metadata={"journal_id": entry_id, "entry_date": entry_date},
            )
            db.commit()
            row = db.execute("select * from journal_entries where id = ?", (entry_id,)).fetchone()
        return self._journal_from_row(row)

    def list_journal_entries(self, *, limit: int = 20) -> list[JournalEntry]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                """
                select * from journal_entries
                order by entry_date desc, datetime(created_at) desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [self._journal_from_row(row) for row in rows]

    def summarize_journal(self) -> JournalSummary:
        entries = self.list_journal_entries(limit=20)
        if not entries:
            return JournalSummary(
                weekly_summary="No journal entries have been saved yet.",
                resume_bullets=[],
                interview_stories=[],
                learning_insights=[],
                citations=[],
            )

        built = [entry.built for entry in entries if entry.built]
        skills = sorted({skill for entry in entries for skill in entry.skills_used})
        next_tasks = [task for entry in entries for task in entry.next_tasks]
        citations = [
            Citation(
                source_id=entry.id,
                title=f"Journal {entry.entry_date}",
                uri=f"journal://{entry.id}",
                snippet=summarize_text(entry.built, max_chars=160),
            )
            for entry in entries[:6]
        ]
        return JournalSummary(
            weekly_summary=(
                f"Across {len(entries)} entries, you built: "
                + "; ".join(built[:5])
                + "."
            ),
            resume_bullets=[
                f"Built {item} using {', '.join(skills[:4]) or 'full-stack engineering'}."
                for item in built[:4]
            ],
            interview_stories=[
                f"Situation: Atlas needed progress on {entry.built}. "
                f"Action: handled {entry.problems or 'implementation tradeoffs'} "
                f"and decided {entry.decisions or 'the next implementation step'}."
                for entry in entries[:3]
            ],
            learning_insights=[
                f"Keep practicing {skill} through Atlas implementation work."
                for skill in skills[:5]
            ]
            + ([f"Next task to preserve momentum: {next_tasks[0]}"] if next_tasks else []),
            citations=citations,
        )

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

    def propose_action(self, payload: ApprovalActionCreate) -> ApprovalAction:
        self.initialize()
        action_id = new_id("act")
        timestamp = now().isoformat()
        preview = self._preview_action(payload.tool_name, payload.title, payload.inputs)
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into approval_actions (
                    id, tool_name, title, status, risk_level, inputs, preview,
                    result, artifact_path, trace_id, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    payload.tool_name,
                    payload.title,
                    "pending",
                    payload.risk_level,
                    encode_json(payload.inputs),
                    preview,
                    encode_json({}),
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
            db.commit()
            row = db.execute(
                "select * from approval_actions where id = ?",
                (action_id,),
            ).fetchone()
        return self._approval_action_from_row(row)

    def list_actions(self) -> list[ApprovalAction]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from approval_actions order by datetime(created_at) desc"
            ).fetchall()
        return [self._approval_action_from_row(row) for row in rows]

    def approve_action(self, action_id: str) -> ApprovalAction | None:
        self.initialize()
        action = self.get_action(action_id)
        if not action:
            return None
        if action.status != "pending":
            return action

        result, artifact_path = self._execute_action(action)
        trace = self.create_trace(
            interaction_type=f"approval:{action.tool_name}",
            user_input=action.title,
            retrieved_memories=[],
            prompt_version="approval-action-v1",
            model_used="atlas-action-tools-v1",
            tool_calls=[{"tool": action.tool_name, "approval_id": action.id}],
            generated_output=result,
            latency_ms=4,
            confidence=0.86,
            assumptions=["Action executed only after explicit approval."],
            steps=[
                TraceStep(
                    name="approval_granted",
                    status="completed",
                    input={"action_id": action.id},
                    output={"tool": action.tool_name},
                    latency_ms=1,
                ),
                TraceStep(
                    name="execute_tool",
                    status="completed",
                    input=action.inputs,
                    output=result,
                    tool_calls=[{"tool": action.tool_name}],
                    latency_ms=3,
                ),
            ],
        )
        with self._lock, self._connect() as db:
            db.execute(
                """
                update approval_actions
                set status = ?, result = ?, artifact_path = ?, trace_id = ?, updated_at = ?
                where id = ?
                """,
                (
                    "approved",
                    encode_json(result),
                    artifact_path,
                    trace.id,
                    now().isoformat(),
                    action_id,
                ),
            )
            if artifact_path:
                db.execute(
                    """
                    insert into artifact_records (
                        id, action_id, title, kind, path, content_preview, created_at
                    )
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("artifact"),
                        action_id,
                        action.title,
                        action.tool_name,
                        artifact_path,
                        summarize_text(result.get("content", ""), max_chars=260),
                        now().isoformat(),
                    ),
                )
            db.commit()
            row = db.execute(
                "select * from approval_actions where id = ?",
                (action_id,),
            ).fetchone()
        return self._approval_action_from_row(row)

    def reject_action(self, action_id: str) -> ApprovalAction | None:
        self.initialize()
        action = self.get_action(action_id)
        if not action:
            return None
        if action.status != "pending":
            return action
        with self._lock, self._connect() as db:
            db.execute(
                "update approval_actions set status = ?, updated_at = ? where id = ?",
                ("rejected", now().isoformat(), action_id),
            )
            db.commit()
            row = db.execute(
                "select * from approval_actions where id = ?",
                (action_id,),
            ).fetchone()
        return self._approval_action_from_row(row)

    def get_action(self, action_id: str) -> ApprovalAction | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "select * from approval_actions where id = ?",
                (action_id,),
            ).fetchone()
        return self._approval_action_from_row(row) if row else None

    def list_artifacts(self) -> list[ArtifactRecord]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from artifact_records order by datetime(created_at) desc"
            ).fetchall()
        return [self._artifact_from_row(row) for row in rows]

    def dashboard_summary(self) -> DashboardSummary:
        self.initialize()
        profile = self.get_profile()
        repos = self.list_repos()[:4]
        workflows = self.list_workflow_runs()
        actions = self.list_actions()
        memories = self.list_memories()[:5]
        traces = self.list_traces()[:5]
        pending_workflows = [run for run in workflows if run.status in {"pending", "running"}][:5]
        pending_approvals = [action for action in actions if action.status == "pending"][:5]
        latest_risks = self._latest_risk_metrics()
        priorities = [
            *(profile.current_goals[:2] or ["Strengthen Atlas with source-backed AI workflows"]),
            "Run a code analysis on the latest repo ZIP.",
            "Convert today’s work into journal evidence.",
        ][:4]
        next_action = (
            "Review and approve the pending artifact action."
            if pending_approvals
            else "Run code intelligence on an indexed project."
            if repos and not self.get_code_graph(repos[0].id)
            else "Create a journal entry and generate resume bullets from it."
        )
        return DashboardSummary(
            metrics={
                "memories": len(self.list_memories()),
                "projects": len(self.list_repos()),
                "traces": len(self.list_traces()),
                "pending_approvals": len([item for item in actions if item.status == "pending"]),
                "symbols": len(self.list_code_symbols(limit=10_000)),
                "risks": latest_risks.get("risks", 0),
            },
            todays_priorities=priorities,
            current_projects=repos,
            pending_workflows=pending_workflows,
            pending_approvals=pending_approvals,
            recent_memories=memories,
            recent_traces=traces,
            weak_areas=profile.weaknesses[:5],
            next_recommended_action=next_action,
        )

    def evaluation_prompts(self) -> list[EvaluationPrompt]:
        return [
            EvaluationPrompt(
                id="resume_bullet_quality",
                category="career",
                prompt="Generate resume bullets from stored Atlas evidence.",
                success_criteria=[
                    "Uses action verbs",
                    "Names technical scope",
                    "Avoids unsupported claims",
                    "Can cite memory or journal evidence",
                ],
            ),
            EvaluationPrompt(
                id="memory_retrieval_accuracy",
                category="memory",
                prompt="Answer a personal context question using retrieval.",
                success_criteria=[
                    "Returns relevant memory",
                    "Includes citations",
                    "Admits when evidence is thin",
                ],
            ),
            EvaluationPrompt(
                id="codebase_qa_correctness",
                category="code",
                prompt="Summarize architecture from repo symbols and graph.",
                success_criteria=[
                    "Uses indexed files",
                    "Mentions graph evidence",
                    "Includes file citations",
                ],
            ),
            EvaluationPrompt(
                id="workflow_reliability",
                category="workflow",
                prompt="Run a named workflow and inspect trace completeness.",
                success_criteria=["Completes run", "Records trace", "Reports assumptions"],
            ),
            EvaluationPrompt(
                id="citation_quality",
                category="traceability",
                prompt="Check whether outputs include source snippets.",
                success_criteria=["Every claim has evidence", "Citations have titles and snippets"],
            ),
            EvaluationPrompt(
                id="hallucination_checks",
                category="safety",
                prompt="Ask for missing facts and verify Atlas avoids inventing them.",
                success_criteria=[
                    "States missing evidence",
                    "Suggests ingestion or profile update",
                ],
            ),
        ]

    def run_evaluations(self) -> EvaluationRun:
        self.initialize()
        prompts = self.evaluation_prompts()
        memories = self.list_memories()
        traces = self.list_traces()
        symbols = self.list_code_symbols(limit=500)
        repos = self.list_repos()
        actions = self.list_actions()
        results: list[dict[str, Any]] = []

        signals = {
            "has_memory": bool(memories),
            "has_citations": any(memory.citations for memory in memories),
            "has_traces": bool(traces),
            "has_code": bool(symbols),
            "has_repo": bool(repos),
            "has_approvals": bool(actions),
        }
        for prompt in prompts:
            score = self._score_eval(prompt.id, signals)
            results.append(
                {
                    "id": prompt.id,
                    "category": prompt.category,
                    "score": score,
                    "status": "pass" if score >= 0.7 else "needs_data",
                    "evidence": self._eval_evidence(prompt.id, signals),
                    "success_criteria": prompt.success_criteria,
                }
            )

        average = round(sum(item["score"] for item in results) / len(results), 2)
        summary = f"Evaluation suite completed with average score {average}."
        trace = self.create_trace(
            interaction_type="evaluation_suite",
            user_input="run local Atlas evaluation suite",
            retrieved_memories=[],
            prompt_version="eval-suite-v1",
            model_used="atlas-deterministic-evals-v1",
            tool_calls=[{"tool": "eval.run", "prompts": len(prompts)}],
            generated_output={"average_score": average, "results": results},
            latency_ms=5,
            confidence=0.82,
            assumptions=["Local evals inspect stored evidence and trace completeness."],
        )
        run_id = new_id("eval")
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into eval_runs (id, status, generated_at, results, summary, trace_id)
                values (?, ?, ?, ?, ?, ?)
                """,
                (run_id, "completed", timestamp, encode_json(results), summary, trace.id),
            )
            db.commit()
            row = db.execute("select * from eval_runs where id = ?", (run_id,)).fetchone()
        return self._eval_run_from_row(row)

    def list_evaluation_runs(self) -> list[EvaluationRun]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from eval_runs order by datetime(generated_at) desc"
            ).fetchall()
        return [self._eval_run_from_row(row) for row in rows]

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

    def knowledge_graph(self) -> KnowledgeGraph:
        self.initialize()
        nodes: dict[str, KnowledgeNode] = {}
        edges: dict[str, KnowledgeEdge] = {}

        def add_node(node_id: str, label: str, kind: str, weight: float = 1.0) -> None:
            nodes.setdefault(
                node_id,
                KnowledgeNode(id=node_id, label=label, kind=kind, weight=weight),
            )

        def add_edge(source: str, target: str, relation: str, evidence: str) -> None:
            edge_id = f"{source}->{relation}->{target}"
            edges.setdefault(
                edge_id,
                KnowledgeEdge(
                    id=edge_id,
                    source=source,
                    target=target,
                    relation=relation,
                    evidence=summarize_text(evidence, max_chars=220),
                ),
            )

        profile = self.get_profile()
        add_node("person:default", profile.name or "Atlas user", "person", 2.0)
        for skill in profile.skills + profile.preferred_tech_stack:
            skill_id = f"skill:{_slug(skill)}"
            add_node(skill_id, skill, "skill", 1.5)
            add_edge("person:default", skill_id, "has_skill", "Profile skill")
        for goal in profile.current_goals + profile.learning_priorities:
            goal_id = f"goal:{_slug(goal)}"
            add_node(goal_id, goal, "goal", 1.3)
            add_edge("person:default", goal_id, "pursues", "Profile goal")

        for repo in self.list_repos():
            repo_id = f"repo:{repo.id}"
            add_node(repo_id, repo.name, "repo", 1.4)
            add_edge("person:default", repo_id, "builds", repo.summary)
            for language in repo.language_stats:
                skill_id = f"skill:{_slug(language)}"
                add_node(skill_id, language, "skill", 1.2)
                add_edge(repo_id, skill_id, "uses", f"{repo.name} uses {language}")

        for memory in self.list_memories()[:200]:
            memory_id = f"memory:{memory.id}"
            label = memory.title or memory.source_title
            add_node(memory_id, label, memory.memory_type, max(0.5, memory.importance))
            add_edge("person:default", memory_id, "remembers", memory.summary)
            for tag in memory.tags[:8]:
                concept_id = f"concept:{_slug(tag)}"
                add_node(concept_id, tag, "concept", 1.0)
                add_edge(memory_id, concept_id, "mentions", memory.summary)

        for decision in self.list_decisions():
            decision_id = f"decision:{decision.id}"
            add_node(decision_id, decision.title, "decision", 1.4)
            add_edge("person:default", decision_id, "decided", decision.reason)
            for tag in decision.tags:
                concept_id = f"concept:{_slug(tag)}"
                add_node(concept_id, tag, "concept", 1.0)
                add_edge(decision_id, concept_id, "relates_to", decision.decision)

        for symbol in self.list_code_symbols(limit=120):
            symbol_id = f"symbol:{symbol.id}"
            add_node(symbol_id, symbol.name, "symbol", 0.9)
            repo_id = f"repo:{symbol.project_id}"
            add_edge(repo_id, symbol_id, "contains", symbol.evidence or symbol.file_path)

        return KnowledgeGraph(
            generated_at=now(),
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            metrics={"nodes": len(nodes), "edges": len(edges)},
        )

    def create_decision(self, payload: DecisionCreate) -> DecisionEntry:
        self.initialize()
        decision_id = new_id("decision")
        timestamp = now().isoformat()
        text = self._decision_text(payload)
        with self._lock, self._connect() as db:
            source_id = self._insert_source(
                db,
                title=payload.title,
                source_type="decision",
                uri=f"decision://{decision_id}",
                raw_text=text,
                metadata={"decision_id": decision_id},
            )
            memory_id = self._insert_memory(
                db,
                source_id=source_id,
                memory_type="decision",
                title=payload.title,
                content=text,
                tags=["decision", *payload.tags],
                importance=0.85,
                metadata={"decision_id": decision_id},
            )
            db.execute(
                """
                insert into decision_entries (
                    id, title, decision, alternatives, tradeoffs, reason,
                    result, tags, memory_id, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    payload.title,
                    payload.decision,
                    encode_json(payload.alternatives),
                    encode_json(payload.tradeoffs),
                    payload.reason,
                    payload.result,
                    encode_json(payload.tags),
                    memory_id,
                    timestamp,
                    timestamp,
                ),
            )
            db.commit()
            row = db.execute(
                "select * from decision_entries where id = ?",
                (decision_id,),
            ).fetchone()
        return self._decision_from_row(row)

    def list_decisions(self) -> list[DecisionEntry]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from decision_entries order by datetime(created_at) desc"
            ).fetchall()
        return [self._decision_from_row(row) for row in rows]

    def update_decision(self, decision_id: str, payload: DecisionUpdate) -> DecisionEntry | None:
        self.initialize()
        current = self.get_decision(decision_id)
        if not current:
            return None
        result = payload.result if payload.result is not None else current.result
        tags = payload.tags if payload.tags is not None else current.tags
        with self._lock, self._connect() as db:
            db.execute(
                """
                update decision_entries
                set result = ?, tags = ?, updated_at = ?
                where id = ?
                """,
                (result, encode_json(tags), now().isoformat(), decision_id),
            )
            db.commit()
            row = db.execute(
                "select * from decision_entries where id = ?",
                (decision_id,),
            ).fetchone()
        return self._decision_from_row(row)

    def get_decision(self, decision_id: str) -> DecisionEntry | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                "select * from decision_entries where id = ?",
                (decision_id,),
            ).fetchone()
        return self._decision_from_row(row) if row else None

    def timeline(self) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        for journal in self.list_journal_entries(limit=80):
            events.append(
                TimelineEvent(
                    id=f"timeline:{journal.id}",
                    event_type="journal",
                    title=f"Built: {journal.built[:80]}",
                    summary=journal.problems or journal.decisions or "Project progress logged.",
                    occurred_at=journal.created_at,
                    metadata={"skills": journal.skills_used, "next_tasks": journal.next_tasks},
                )
            )
        for decision in self.list_decisions():
            events.append(
                TimelineEvent(
                    id=f"timeline:{decision.id}",
                    event_type="decision",
                    title=decision.title,
                    summary=decision.decision,
                    occurred_at=decision.created_at,
                    metadata={"tags": decision.tags, "result": decision.result},
                )
            )
        for run in self.list_workflow_runs()[:80]:
            events.append(
                TimelineEvent(
                    id=f"timeline:{run.id}",
                    event_type="workflow",
                    title=run.workflow_name,
                    summary=summarize_text(encode_json(run.outputs), max_chars=220),
                    occurred_at=run.created_at,
                    metadata={"status": run.status, "trace_id": run.trace_id},
                )
            )
        for artifact in self.list_artifacts():
            events.append(
                TimelineEvent(
                    id=f"timeline:{artifact.id}",
                    event_type="artifact",
                    title=artifact.title,
                    summary=artifact.content_preview,
                    occurred_at=artifact.created_at,
                    metadata={"path": artifact.path, "kind": artifact.kind},
                )
            )
        for repo in self.list_repos():
            events.append(
                TimelineEvent(
                    id=f"timeline:{repo.id}",
                    event_type="project",
                    title=f"Indexed {repo.name}",
                    summary=repo.summary,
                    occurred_at=repo.created_at,
                    metadata={"status": repo.status, "languages": repo.language_stats},
                )
            )
        return sorted(events, key=lambda event: event.occurred_at, reverse=True)

    def skill_tree(self) -> SkillTreeResponse:
        profile = self.get_profile()
        journals = self.list_journal_entries(limit=100)
        repos = self.list_repos()
        symbols = self.list_code_symbols(limit=500)
        evidence: dict[str, list[str]] = {}

        def add(skill: str, item: str) -> None:
            evidence.setdefault(skill, [])
            if item not in evidence[skill]:
                evidence[skill].append(item)

        for skill in profile.skills + profile.preferred_tech_stack + profile.learning_priorities:
            add(skill, "Profile")
        for journal in journals:
            for skill in journal.skills_used:
                add(skill, f"Journal {journal.entry_date}")
        for repo in repos:
            for language in repo.language_stats:
                add(language, f"Repo {repo.name}")
        for symbol in symbols:
            if symbol.language:
                add(symbol.language, f"{symbol.file_path}:{symbol.line_start}")

        skills: list[SkillTreeItem] = []
        for name, items in sorted(evidence.items()):
            category = _skill_category(name)
            progress = min(100, 20 + len(items) * 16)
            level = max(1, min(5, progress // 20))
            skills.append(
                SkillTreeItem(
                    id=f"skilltree:{_slug(name)}",
                    category=category,
                    name=name,
                    level=level,
                    progress=progress,
                    evidence=items[:8],
                    next_action=f"Create one Atlas task that uses {name} and log the result.",
                )
            )
        return SkillTreeResponse(
            generated_at=now(),
            skills=skills,
            metrics={
                "skills": len(skills),
                "categories": len({skill.category for skill in skills}),
                "evidence_items": sum(len(skill.evidence) for skill in skills),
            },
        )

    def self_evaluate(self, payload: SelfEvaluationRequest) -> SelfEvaluationResponse:
        sources = [citation.title for citation in payload.citations]
        snippets = payload.source_snippets + [citation.snippet for citation in payload.citations]
        output_lower = payload.output.lower()
        evidence_hits = sum(
            1
            for snippet in snippets
            if snippet and any(term in output_lower for term in snippet.lower().split()[:8])
        )
        grounded = bool(payload.citations or evidence_hits)
        confidence = round(
            0.45 + (0.2 if payload.citations else 0) + min(0.3, evidence_hits * 0.1),
            2,
        )
        verification_items = []
        if not payload.citations:
            verification_items.append(
                "Add citations or source snippets before trusting this output."
            )
        if "always" in output_lower or "guarantee" in output_lower:
            verification_items.append("Verify absolute claims such as always/guarantee.")
        if len(payload.output.split()) < 25:
            verification_items.append(
                "Output is short; verify it covers the user's actual context."
            )
        risk = "low" if grounded and confidence >= 0.75 else "medium" if grounded else "high"
        critique = (
            "Output is grounded in cited evidence."
            if grounded
            else "Output lacks direct source evidence and should be treated as ungrounded."
        )
        trace = self.create_trace(
            interaction_type="self_evaluation",
            user_input=payload.prompt or payload.output[:160],
            retrieved_memories=[],
            prompt_version="self-eval-v1",
            model_used="atlas-deterministic-self-eval-v1",
            tool_calls=[{"tool": "self.evaluate", "citations": len(payload.citations)}],
            generated_output={
                "grounded": grounded,
                "confidence": confidence,
                "hallucination_risk": risk,
                "verification_items": verification_items,
            },
            latency_ms=4,
            confidence=confidence,
            assumptions=[
                "Self-evaluation uses citations, snippets, and conservative claim checks."
            ],
        )
        return SelfEvaluationResponse(
            grounded=grounded,
            confidence=confidence,
            hallucination_risk=risk,
            sources_used=sources,
            verification_items=verification_items,
            critique=critique,
            trace_id=trace.id,
        )

    def simulator_scenarios(self) -> list[SimulatorScenario]:
        return [
            SimulatorScenario(
                id="system_design_ai_os",
                scenario_type="system_design",
                title="Design a personal AI OS",
                prompt=(
                    "Design Atlas for one developer: memory, retrieval, workflows, approvals, "
                    "code intelligence, traces, and local-first privacy."
                ),
                rubric=[
                    "Clear architecture boundaries",
                    "Privacy and approval model",
                    "Traceability",
                    "Scaling and failure modes",
                ],
            ),
            SimulatorScenario(
                id="debugging_incident_retrieval",
                scenario_type="debugging_incident",
                title="Retrieval quality incident",
                prompt="Atlas starts returning generic answers with weak citations. Investigate.",
                rubric=[
                    "Checks retrieval inputs",
                    "Inspects traces",
                    "Validates source evidence",
                    "Proposes regression tests",
                ],
            ),
            SimulatorScenario(
                id="production_outage_worker",
                scenario_type="production_outage",
                title="Workflow worker outage",
                prompt="Workflow runs are stuck pending after a deploy. Walk through response.",
                rubric=["Triage", "Rollback/mitigation", "Observability", "Prevention"],
            ),
            SimulatorScenario(
                id="behavioral_decision",
                scenario_type="behavioral_interview",
                title="Explain a hard technical decision",
                prompt="Use Atlas as the project. Explain a decision, tradeoffs, and result.",
                rubric=["Situation", "Tradeoffs", "Action", "Learning"],
            ),
        ]

    def start_simulation(self, payload: SimulationStartRequest) -> SimulationRun:
        scenario = next(
            (item for item in self.simulator_scenarios() if item.id == payload.scenario_id),
            None,
        )
        if not scenario:
            raise ValueError(f"Unknown scenario: {payload.scenario_id}")
        run_id = new_id("sim")
        timestamp = now().isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert into simulation_runs (
                    id, scenario_id, scenario_type, title, prompt, rubric, status,
                    answer, evaluation, trace_id, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    scenario.id,
                    scenario.scenario_type,
                    scenario.title,
                    scenario.prompt,
                    encode_json(scenario.rubric),
                    "running",
                    None,
                    encode_json({}),
                    None,
                    timestamp,
                    timestamp,
                ),
            )
            db.commit()
            row = db.execute("select * from simulation_runs where id = ?", (run_id,)).fetchone()
        return self._simulation_from_row(row)

    def answer_simulation(
        self,
        run_id: str,
        payload: SimulationAnswerRequest,
    ) -> SimulationRun | None:
        current = self.get_simulation(run_id)
        if not current:
            return None
        evaluation = self._evaluate_simulation_answer(current.scenario, payload.answer)
        trace = self.create_trace(
            interaction_type="simulator:evaluate_answer",
            user_input=payload.answer,
            retrieved_memories=[],
            prompt_version="simulator-v1",
            model_used="atlas-deterministic-simulator-v1",
            tool_calls=[{"tool": "simulator.evaluate", "scenario": current.scenario.id}],
            generated_output=evaluation,
            latency_ms=5,
            confidence=0.8,
            assumptions=["Simulator scoring is deterministic and rubric-based."],
        )
        with self._lock, self._connect() as db:
            db.execute(
                """
                update simulation_runs
                set answer = ?, evaluation = ?, status = ?, trace_id = ?, updated_at = ?
                where id = ?
                """,
                (
                    payload.answer,
                    encode_json(evaluation),
                    "completed",
                    trace.id,
                    now().isoformat(),
                    run_id,
                ),
            )
            db.commit()
            row = db.execute("select * from simulation_runs where id = ?", (run_id,)).fetchone()
        return self._simulation_from_row(row)

    def list_simulations(self) -> list[SimulationRun]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute(
                "select * from simulation_runs order by datetime(created_at) desc"
            ).fetchall()
        return [self._simulation_from_row(row) for row in rows]

    def get_simulation(self, run_id: str) -> SimulationRun | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from simulation_runs where id = ?", (run_id,)).fetchone()
        return self._simulation_from_row(row) if row else None

    def list_plugins(self) -> list[PluginManifest]:
        self.initialize()
        with self._connect() as db:
            rows = db.execute("select * from plugin_registry order by category, name").fetchall()
        return [self._plugin_from_row(row) for row in rows]

    def update_plugin(self, plugin_id: str, payload: PluginUpdate) -> PluginManifest | None:
        self.initialize()
        current = self.get_plugin(plugin_id)
        if not current:
            return None
        enabled = current.enabled if payload.enabled is None else payload.enabled
        config = current.config if payload.config is None else payload.config
        with self._lock, self._connect() as db:
            db.execute(
                """
                update plugin_registry
                set enabled = ?, config = ?, updated_at = ?
                where id = ?
                """,
                (int(enabled), encode_json(config), now().isoformat(), plugin_id),
            )
            db.commit()
            row = db.execute("select * from plugin_registry where id = ?", (plugin_id,)).fetchone()
        return self._plugin_from_row(row)

    def get_plugin(self, plugin_id: str) -> PluginManifest | None:
        self.initialize()
        with self._connect() as db:
            row = db.execute("select * from plugin_registry where id = ?", (plugin_id,)).fetchone()
        return self._plugin_from_row(row) if row else None

    def model_providers(self) -> list[ModelProvider]:
        settings = get_settings()
        return [
            ModelProvider(
                id="openai",
                name="OpenAI-compatible cloud",
                mode="cloud",
                endpoint=None,
                status="configured" if settings.openai_api_key else "needs_key",
                notes="Uses ATLAS_OPENAI_API_KEY when cloud calls are enabled.",
            ),
            ModelProvider(
                id="ollama",
                name="Ollama",
                mode="local",
                endpoint="http://localhost:11434",
                status="available_if_running",
                notes="Local model endpoint for offline development.",
            ),
            ModelProvider(
                id="vllm",
                name="vLLM OpenAI-compatible server",
                mode="local",
                endpoint="http://localhost:8001/v1",
                status="available_if_running",
                notes="Hybrid deployment path for local or private GPU inference.",
            ),
        ]

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def _ensure_profile(self, db: sqlite3.Connection) -> None:
        exists = db.execute("select 1 from user_profiles where id = ?", ("default",)).fetchone()
        if exists:
            return
        timestamp = now().isoformat()
        db.execute(
            """
            insert into user_profiles (
                id, name, role, current_goals, target_roles, skills, weaknesses,
                preferred_tech_stack, learning_priorities, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "default",
                "",
                "Student / Developer",
                encode_json(["Build Atlas into a recruiter-impressive AI engineering project"]),
                encode_json(["AI Product Engineer", "Backend Engineer", "Full-stack AI Engineer"]),
                encode_json(["Python", "FastAPI", "TypeScript", "React", "PostgreSQL"]),
                encode_json(["Production AI evaluation", "System design interview depth"]),
                encode_json(
                    ["Next.js", "TypeScript", "Tailwind", "FastAPI", "PostgreSQL", "Redis"]
                ),
                encode_json(
                    [
                        "LangGraph or Agents SDK",
                        "pgvector retrieval",
                        "tree-sitter code intelligence",
                    ]
                ),
                timestamp,
            ),
        )

    def _ensure_seed_memory(self, db: sqlite3.Connection) -> None:
        exists = db.execute("select 1 from memories limit 1").fetchone()
        if exists:
            return
        source_id = self._insert_source(
            db,
            title="Atlas Product Scope",
            source_type="note",
            uri="docs/product-spec.md",
            raw_text=(
                "Atlas is a private, traceable personal AI OS for engineering, "
                "learning, and career growth."
            ),
            metadata={"seed": True},
        )
        self._insert_memory(
            db,
            source_id=source_id,
            memory_type="decision",
            title="Atlas core promise",
            content=(
                "Atlas should be context-aware, source-backed, approval-gated, "
                "and useful for projects, learning, code review, interviews, "
                "and career artifacts."
            ),
            tags=["atlas", "product", "career"],
            importance=0.9,
            metadata={"seed": True},
        )

    def _ensure_privacy_settings(self, db: sqlite3.Connection) -> None:
        exists = db.execute("select 1 from privacy_settings where id = ?", ("default",)).fetchone()
        if exists:
            return
        root = str(_workspace_root())
        db.execute(
            """
            insert into privacy_settings (
                id, allowed_folders, blocked_folders, redaction_patterns,
                local_only, memory_export_enabled, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "default",
                encode_json([root]),
                encode_json([str(Path.home() / ".ssh"), str(Path.home() / ".aws")]),
                encode_json(_default_redaction_patterns()),
                1,
                1,
                now().isoformat(),
            ),
        )

    def _ensure_plugins(self, db: sqlite3.Connection) -> None:
        exists = db.execute("select 1 from plugin_registry limit 1").fetchone()
        if exists:
            return
        timestamp = now().isoformat()
        plugins = [
            (
                "github",
                "GitHub Plugin",
                "connector",
                "Draft issues and later create PR/issue actions after approval.",
                0,
                ["repo:read", "repo:write_after_approval"],
            ),
            (
                "calendar",
                "Calendar Plugin",
                "connector",
                "Plan blocks and interview prep sessions with explicit approval.",
                0,
                ["calendar:read", "calendar:write_after_approval"],
            ),
            (
                "file",
                "File Plugin",
                "local",
                "Create local Markdown artifacts inside approved folders.",
                1,
                ["file:write_artifacts"],
            ),
            (
                "resume",
                "Resume Plugin",
                "career",
                "Parse resumes and generate cited resume artifacts.",
                1,
                ["resume:read", "artifact:write_after_approval"],
            ),
            (
                "repo_analyzer",
                "Repo Analyzer Plugin",
                "code",
                "Ingest ZIPs, extract symbols, build graphs, and produce risk reports.",
                1,
                ["repo:read_uploaded_zip", "code:analyze"],
            ),
            (
                "interview_coach",
                "Interview Coach Plugin",
                "career",
                "Run simulator scenarios and evaluate answers.",
                1,
                ["memory:read", "simulation:evaluate"],
            ),
        ]
        for plugin in plugins:
            db.execute(
                """
                insert into plugin_registry (
                    id, name, category, description, enabled, permission_scopes,
                    status, config, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plugin[0],
                    plugin[1],
                    plugin[2],
                    plugin[3],
                    plugin[4],
                    encode_json(plugin[5]),
                    "available",
                    encode_json({}),
                    timestamp,
                ),
            )

    def _insert_source(
        self,
        db: sqlite3.Connection,
        *,
        title: str,
        source_type: str,
        uri: str | None,
        raw_text: str,
        metadata: dict[str, Any],
    ) -> str:
        source_id = new_id("src")
        db.execute(
            """
            insert into source_documents (
                id, title, source_type, uri, raw_text, metadata, created_at
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                title,
                source_type,
                uri,
                raw_text,
                encode_json(metadata),
                now().isoformat(),
            ),
        )
        return source_id

    def _upsert_source(
        self,
        db: sqlite3.Connection,
        *,
        title: str,
        source_type: str,
        uri: str,
        raw_text: str,
        metadata: dict[str, Any],
    ) -> str:
        row = db.execute("select id from source_documents where uri = ?", (uri,)).fetchone()
        if row:
            db.execute(
                "update source_documents set raw_text = ?, metadata = ? where id = ?",
                (raw_text, encode_json(metadata), row["id"]),
            )
            return str(row["id"])
        return self._insert_source(
            db, title=title, source_type=source_type, uri=uri, raw_text=raw_text, metadata=metadata
        )

    def _insert_memory(
        self,
        db: sqlite3.Connection,
        *,
        source_id: str,
        memory_type: str,
        title: str,
        content: str,
        tags: list[str],
        importance: float,
        metadata: dict[str, Any],
    ) -> str:
        memory_id = new_id("mem")
        timestamp = now().isoformat()
        summary = summarize_text(content)
        embedding = embed_text(f"{title}\n{content}", self.embedding_dimensions)
        source = db.execute("select * from source_documents where id = ?", (source_id,)).fetchone()
        citation = {
            "source_id": source_id,
            "title": source["title"] if source else title,
            "uri": source["uri"] if source else None,
            "snippet": summarize_text(content, max_chars=180),
        }
        metadata_with_embedding = dict(metadata)
        metadata_with_embedding["_embedding"] = embedding
        db.execute(
            """
            insert into memories (
                id, source_id, memory_type, title, content, summary, tags, importance,
                source_references, metadata, embedding, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                source_id,
                memory_type,
                title,
                content,
                summary,
                encode_json(tags),
                max(0.0, min(1.0, importance)),
                encode_json([citation]),
                encode_json(metadata_with_embedding),
                encode_json(embedding),
                timestamp,
                timestamp,
            ),
        )
        return memory_id

    def _upsert_profile_memory(
        self, db: sqlite3.Connection, source_id: str, payload: UserProfileUpdate
    ) -> None:
        db.execute("delete from memories where source_id = ?", (source_id,))
        sections = {
            "goals": payload.current_goals,
            "target roles": payload.target_roles,
            "skills": payload.skills,
            "weaknesses": payload.weaknesses,
            "preferred tech stack": payload.preferred_tech_stack,
            "learning priorities": payload.learning_priorities,
        }
        for label, values in sections.items():
            if not values:
                continue
            self._insert_memory(
                db,
                source_id=source_id,
                memory_type="goal" if label in {"goals", "learning priorities"} else "note",
                title=f"Profile {label}",
                content="\n".join(values),
                tags=["profile", label],
                importance=0.8,
                metadata={"profile_field": label},
            )

    def _insert_resume_memories(
        self,
        db: sqlite3.Connection,
        source_id: str,
        structured: StructuredResume,
        raw_text: str,
    ) -> list[str]:
        memory_ids: list[str] = []
        for section, values in structured.as_dict().items():
            if not values:
                continue
            memory_ids.append(
                self._insert_memory(
                    db,
                    source_id=source_id,
                    memory_type="resume",
                    title=f"Resume {section}",
                    content="\n".join(values),
                    tags=["resume", section],
                    importance=0.9,
                    metadata={"resume_section": section},
                )
            )

        for index, chunk in enumerate(chunk_text(raw_text, max_chars=1200)):
            memory_ids.append(
                self._insert_memory(
                    db,
                    source_id=source_id,
                    memory_type="resume",
                    title=f"Resume raw text chunk {index + 1}",
                    content=chunk,
                    tags=["resume", "raw"],
                    importance=0.65,
                    metadata={"resume_section": "raw", "chunk_index": index},
                )
            )
        return memory_ids

    def _memory_row(self, db: sqlite3.Connection, memory_id: str) -> sqlite3.Row | None:
        return db.execute(
            """
            select memories.*, source_documents.title as source_title,
                   source_documents.source_type as source_type,
                   source_documents.uri as source_uri
            from memories
            join source_documents on source_documents.id = memories.source_id
            where memories.id = ?
            """,
            (memory_id,),
        ).fetchone()

    def _profile_from_row(self, row: sqlite3.Row) -> UserProfile:
        return UserProfile(
            id=row["id"],
            name=row["name"],
            role=row["role"],
            current_goals=decode_json(row["current_goals"], []),
            target_roles=decode_json(row["target_roles"], []),
            skills=decode_json(row["skills"], []),
            weaknesses=decode_json(row["weaknesses"], []),
            preferred_tech_stack=decode_json(row["preferred_tech_stack"], []),
            learning_priorities=decode_json(row["learning_priorities"], []),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _source_from_row(self, row: sqlite3.Row) -> SourceDocument:
        return SourceDocument(
            id=row["id"],
            title=row["title"],
            source_type=row["source_type"],
            uri=row["uri"],
            metadata=decode_json(row["metadata"], {}),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _memory_from_row(self, row: sqlite3.Row) -> MemoryItem:
        references = [Citation(**item) for item in decode_json(row["source_references"], [])]
        metadata = decode_json(row["metadata"], {})
        metadata.pop("_embedding", None)
        return MemoryItem(
            id=row["id"],
            source_id=row["source_id"],
            source_title=row["source_title"],
            source_type=row["source_type"],
            memory_type=row["memory_type"],
            title=row["title"],
            content=row["content"],
            summary=row["summary"],
            tags=decode_json(row["tags"], []),
            importance=row["importance"],
            source_references=references,
            metadata=metadata,
            confidence=max(0.1, min(1.0, row["importance"])),
            citations=references,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _resume_from_row(self, row: sqlite3.Row) -> ResumeProfile:
        return ResumeProfile(
            id=row["id"],
            source_id=row["source_id"],
            filename=row["filename"],
            raw_text=row["raw_text"],
            structured=ResumeStructuredProfile(**decode_json(row["structured"], {})),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _keyword_score(self, query: str, content: str) -> float:
        query_terms = {term.lower() for term in query.split() if len(term) > 2}
        if not query_terms:
            return 0.0
        content_lower = content.lower()
        matches = sum(1 for term in query_terms if term in content_lower)
        return matches / len(query_terms)

    def _profile_text(self, payload: UserProfileUpdate) -> str:
        return "\n".join(
            [
                f"Name: {payload.name}",
                f"Role: {payload.role}",
                "Current goals: " + "; ".join(payload.current_goals),
                "Target roles: " + "; ".join(payload.target_roles),
                "Skills: " + "; ".join(payload.skills),
                "Weaknesses: " + "; ".join(payload.weaknesses),
                "Preferred tech stack: " + "; ".join(payload.preferred_tech_stack),
                "Learning priorities: " + "; ".join(payload.learning_priorities),
            ]
        )

    def _workflow_output(
        self,
        workflow_name: str,
        inputs: dict[str, Any],
        profile: UserProfile,
        hits: list[RetrievalHit],
        journals: list[JournalEntry],
    ) -> dict[str, Any]:
        evidence = [hit.summary for hit in hits[:4]]
        target = str(inputs.get("target_role") or inputs.get("role") or "AI engineering")
        focus = str(inputs.get("focus") or inputs.get("theme") or "Atlas execution")
        project = str(inputs.get("project") or "Atlas")
        question = str(inputs.get("question") or "Tell me about a technical project.")
        skills = profile.skills + profile.preferred_tech_stack
        weaknesses = profile.weaknesses or ["No weak areas stored yet"]
        journal_summary = self.summarize_journal()

        if workflow_name == "plan_my_day":
            return {
                "plan": [
                    f"Ship one visible Atlas improvement around {focus}.",
                    "Review the highest-signal memory and resume evidence before coding.",
                    "Log progress in the project journal before stopping.",
                ],
                "evidence": evidence,
            }
        if workflow_name == "plan_my_week":
            return {
                "weekly_theme": focus,
                "milestones": [
                    "Implement one backend capability with tests.",
                    "Make the UI operate the capability end to end.",
                    "Convert the work into resume and interview artifacts.",
                ],
                "journal_context": journal_summary.weekly_summary,
            }
        if workflow_name == "create_project_journal":
            entry = self.create_journal_entry(
                JournalEntryCreate(
                    built=str(inputs.get("built") or focus),
                    problems=str(inputs.get("problems") or ""),
                    decisions=str(inputs.get("decisions") or ""),
                    skills_used=list(inputs.get("skills_used") or skills[:3]),
                    next_tasks=list(inputs.get("next_tasks") or ["Continue Atlas checkpoint"]),
                )
            )
            return {"journal_entry": entry.model_dump(mode="json")}
        if workflow_name in {"generate_resume_bullets", "project_to_resume_bullets"}:
            return {
                "target_role": target,
                "bullets": [
                    (
                        f"Built {project}, a private AI OS with memory, retrieval, "
                        "approvals, and traces."
                    ),
                    (
                        "Implemented full-stack workflows across FastAPI, React, "
                        "persistent memory, and cited outputs."
                    ),
                    (
                        "Converted project logs and resume evidence into "
                        "recruiter-ready career artifacts."
                    ),
                ],
                "evidence": evidence,
            }
        if workflow_name in {"prepare_interview_answer", "interview_story_generator"}:
            return {
                "question": question,
                "answer": (
                    "I built Atlas as a realistic personal AI OS. The challenge was making it "
                    "context-aware and traceable rather than a generic chatbot. I implemented "
                    "profile, resume, memory, retrieval, workflow, journal, and trace systems so "
                    "every output can point back to evidence."
                ),
                "star": {
                    "situation": "Needed a recruiter-impressive AI engineering project.",
                    "task": "Build a private, useful AI OS with traceable workflows.",
                    "action": (
                        "Implemented backend services, UI flows, memory, "
                        "and workflow traces."
                    ),
                    "result": "Atlas can now produce grounded career and learning guidance.",
                },
            }
        if workflow_name == "suggest_learning_plan":
            priorities = profile.learning_priorities or weaknesses
            return {
                "learning_plan": [
                    f"Practice {item} through a concrete Atlas feature."
                    for item in priorities[:5]
                ],
                "proof_tasks": [
                    "Add tests for the feature.",
                    "Write a project journal entry.",
                    "Generate one resume bullet from the work.",
                ],
            }
        if workflow_name == "resume_gap_analysis":
            return {
                "target_role": target,
                "gaps": weaknesses,
                "recommended_evidence": [
                    "Add measurable outcomes to project bullets.",
                    "Log system design tradeoffs in the journal.",
                    "Ingest one repo ZIP so code evidence appears in Atlas.",
                ],
            }
        if workflow_name == "role_match_analysis":
            matched = [skill for skill in skills if skill.lower() in " ".join(evidence).lower()]
            return {
                "role": target,
                "match_score": min(88, 55 + len(matched) * 6),
                "matching_strengths": matched[:6] or skills[:6],
                "risks": weaknesses,
            }
        if workflow_name == "skill_growth_plan":
            skill = str(inputs.get("skill") or (weaknesses[0] if weaknesses else "system design"))
            return {
                "skill": skill,
                "growth_plan": [
                    f"Study one focused concept in {skill}.",
                    f"Apply {skill} directly in Atlas.",
                    "Write a journal entry capturing the decision and tradeoff.",
                    "Convert the result into an interview story.",
                ],
            }
        if workflow_name in {
            "architecture_summary",
            "onboarding_guide",
            "refactor_plan",
            "test_plan",
            "PR_review_draft",
            "bug_investigation_plan",
        }:
            repo = self._workflow_repo(inputs)
            if not repo:
                return {
                    "summary": "No indexed repository found.",
                    "next_step": (
                        "Upload a repository ZIP on the Projects page, "
                        "then run code analysis."
                    ),
                }
            graph = self.get_code_graph(repo.id)
            risks = self.get_code_risks(repo.id)
            symbols = self.list_code_symbols(project_id=repo.id, limit=20)
            if not graph or not risks:
                analysis = self.analyze_codebase(repo.id)
                graph = analysis.graph if analysis else graph
                risks = analysis.risk_report if analysis else risks
                symbols = self.list_code_symbols(project_id=repo.id, limit=20)

            risk_items = risks.risks[:8] if risks else []
            symbol_citations = [
                f"{symbol.file_path}:{symbol.line_start} `{symbol.name}`"
                for symbol in symbols[:8]
            ]
            risk_citations = [
                f"{risk.file_path or repo.name}:{risk.line or 1} {risk.title}"
                for risk in risk_items
            ]
            if workflow_name == "architecture_summary":
                return {
                    "repository": repo.name,
                    "summary": repo.summary,
                    "graph_metrics": graph.metrics if graph else {},
                    "main_symbols": symbol_citations,
                    "file_citations": symbol_citations[:6],
                }
            if workflow_name == "onboarding_guide":
                return {
                    "repository": repo.name,
                    "start_here": repo.dependency_files[:5] or ["README.md"],
                    "important_symbols": symbol_citations[:8],
                    "risks_to_notice": risk_citations[:5],
                }
            if workflow_name == "refactor_plan":
                return {
                    "repository": repo.name,
                    "prioritized_changes": [
                        f"{risk.severity.upper()}: {risk.title} - {risk.detail}"
                        for risk in risk_items[:6]
                    ],
                    "evidence": risk_citations[:6],
                }
            if workflow_name == "test_plan":
                missing_tests = [risk for risk in risk_items if risk.category == "missing_tests"]
                return {
                    "repository": repo.name,
                    "test_targets": [
                        risk.file_path or risk.evidence
                        for risk in (missing_tests or risk_items)[:8]
                    ],
                    "strategy": [
                        "Cover public functions and routes first.",
                        "Add regression tests around dependency hotspots.",
                        "Use risk evidence to choose the smallest useful tests.",
                    ],
                    "evidence": risk_citations[:8],
                }
            if workflow_name == "PR_review_draft":
                return {
                    "repository": repo.name,
                    "review_summary": risks.summary if risks else repo.summary,
                    "findings": [
                        {
                            "severity": risk.severity,
                            "title": risk.title,
                            "evidence": risk.evidence,
                        }
                        for risk in risk_items[:6]
                    ],
                    "file_citations": risk_citations[:6],
                }
            symptom = str(inputs.get("symptom") or "unknown bug")
            return {
                "repository": repo.name,
                "symptom": symptom,
                "investigation_path": [
                    "Search symbols related to the failing behavior.",
                    "Inspect import edges around the nearest hotspot.",
                    "Check TODO/FIXME and missing-test risks for nearby files.",
                    "Add a failing regression test before editing.",
                ],
                "candidate_files": [symbol.file_path for symbol in symbols[:8]],
                "evidence": [*symbol_citations[:4], *risk_citations[:4]],
            }
        return {"summary": "Workflow completed.", "evidence": evidence}

    def _workflow_repo(self, inputs: dict[str, Any]) -> RepoProject | None:
        project_id = str(inputs.get("project_id") or "")
        if project_id:
            repo = self.get_repo(project_id)
            if repo:
                return repo
        repos = self.list_repos()
        return repos[0] if repos else None

    def _trace_from_row(self, row: sqlite3.Row) -> TraceRun:
        return TraceRun(
            id=row["id"],
            interaction_type=row["interaction_type"],
            user_input=row["user_input"],
            retrieved_memories=[
                RetrievalHit(**item) for item in decode_json(row["retrieved_memories"], [])
            ],
            prompt_version=row["prompt_version"],
            model_used=row["model_used"],
            tool_calls=decode_json(row["tool_calls"], []),
            generated_output=decode_json(row["generated_output"], {}),
            latency_ms=row["latency_ms"],
            errors=decode_json(row["errors"], []),
            confidence=row["confidence"],
            assumptions=decode_json(row["assumptions"], []),
            steps=[TraceStep(**item) for item in decode_json(row["steps"], [])],
            workflow_run_id=row["workflow_run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _workflow_from_row(self, row: sqlite3.Row) -> WorkflowRunDetail:
        return WorkflowRunDetail(
            id=row["id"],
            workflow_name=row["workflow_name"],
            status=row["status"],
            inputs=decode_json(row["inputs"], {}),
            outputs=decode_json(row["outputs"], {}),
            steps=[TraceStep(**item) for item in decode_json(row["steps"], [])],
            trace_id=row["trace_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _journal_from_row(self, row: sqlite3.Row) -> JournalEntry:
        return JournalEntry(
            id=row["id"],
            built=row["built"],
            problems=row["problems"],
            decisions=row["decisions"],
            skills_used=decode_json(row["skills_used"], []),
            next_tasks=decode_json(row["next_tasks"], []),
            entry_date=row["entry_date"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _journal_text(self, payload: JournalEntryCreate) -> str:
        return "\n".join(
            [
                f"Built: {payload.built}",
                f"Problems: {payload.problems}",
                f"Decisions: {payload.decisions}",
                "Skills used: " + ", ".join(payload.skills_used),
                "Next tasks: " + ", ".join(payload.next_tasks),
            ]
        )

    def _code_symbol_from_row(self, row: sqlite3.Row) -> CodeSymbol:
        return CodeSymbol(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            kind=row["kind"],
            file_path=row["file_path"],
            language=row["language"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            signature=row["signature"],
            evidence=row["evidence"],
            metadata=decode_json(row["metadata"], {}),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _code_graph_from_row(self, row: sqlite3.Row) -> CodeGraph:
        return CodeGraph(
            project_id=row["project_id"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            parser_provider=row["parser_provider"],
            nodes=decode_json(row["nodes"], []),
            edges=decode_json(row["edges"], []),
            metrics=decode_json(row["metrics"], {}),
        )

    def _code_risk_report_from_row(self, row: sqlite3.Row) -> CodeRiskReport:
        return CodeRiskReport(
            project_id=row["project_id"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            summary=row["summary"],
            risks=[CodeRiskItem(**item) for item in decode_json(row["risks"], [])],
            metrics=decode_json(row["metrics"], {}),
        )

    def _approval_action_from_row(self, row: sqlite3.Row) -> ApprovalAction:
        return ApprovalAction(
            id=row["id"],
            tool_name=row["tool_name"],
            title=row["title"],
            status=row["status"],
            risk_level=row["risk_level"],
            inputs=decode_json(row["inputs"], {}),
            preview=row["preview"],
            result=decode_json(row["result"], {}),
            artifact_path=row["artifact_path"],
            trace_id=row["trace_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _artifact_from_row(self, row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            id=row["id"],
            action_id=row["action_id"],
            title=row["title"],
            kind=row["kind"],
            path=row["path"],
            content_preview=row["content_preview"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _eval_run_from_row(self, row: sqlite3.Row) -> EvaluationRun:
        return EvaluationRun(
            id=row["id"],
            status=row["status"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            results=decode_json(row["results"], []),
            summary=row["summary"],
            trace_id=row["trace_id"],
        )

    def _privacy_from_row(self, row: sqlite3.Row) -> PrivacySettings:
        return PrivacySettings(
            id=row["id"],
            allowed_folders=decode_json(row["allowed_folders"], []),
            blocked_folders=decode_json(row["blocked_folders"], []),
            redaction_patterns=decode_json(row["redaction_patterns"], []),
            local_only=bool(row["local_only"]),
            memory_export_enabled=bool(row["memory_export_enabled"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _decision_from_row(self, row: sqlite3.Row) -> DecisionEntry:
        return DecisionEntry(
            id=row["id"],
            title=row["title"],
            decision=row["decision"],
            alternatives=decode_json(row["alternatives"], []),
            tradeoffs=decode_json(row["tradeoffs"], []),
            reason=row["reason"],
            result=row["result"],
            tags=decode_json(row["tags"], []),
            memory_id=row["memory_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _decision_text(self, payload: DecisionCreate) -> str:
        return "\n".join(
            [
                f"Decision: {payload.decision}",
                "Alternatives: " + "; ".join(payload.alternatives),
                "Tradeoffs: " + "; ".join(payload.tradeoffs),
                f"Reason: {payload.reason}",
                f"Result: {payload.result or 'Pending'}",
            ]
        )

    def _simulation_from_row(self, row: sqlite3.Row) -> SimulationRun:
        scenario = SimulatorScenario(
            id=row["scenario_id"],
            scenario_type=row["scenario_type"],
            title=row["title"],
            prompt=row["prompt"],
            rubric=decode_json(row["rubric"], []),
        )
        return SimulationRun(
            id=row["id"],
            scenario=scenario,
            status=row["status"],
            answer=row["answer"],
            evaluation=decode_json(row["evaluation"], {}),
            trace_id=row["trace_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _plugin_from_row(self, row: sqlite3.Row) -> PluginManifest:
        return PluginManifest(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            description=row["description"],
            enabled=bool(row["enabled"]),
            permission_scopes=decode_json(row["permission_scopes"], []),
            status=row["status"],
            config=decode_json(row["config"], {}),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _evaluate_simulation_answer(
        self,
        scenario: SimulatorScenario,
        answer: str,
    ) -> dict[str, Any]:
        answer_lower = answer.lower()
        rubric_scores: list[dict[str, Any]] = []
        for item in scenario.rubric:
            terms = [term for term in re.split(r"[^a-z0-9]+", item.lower()) if len(term) > 3]
            matched = any(term in answer_lower for term in terms)
            rubric_scores.append(
                {
                    "criterion": item,
                    "score": 1 if matched else 0,
                    "feedback": "Covered" if matched else "Needs stronger explicit coverage",
                }
            )
        keyword_bonus = sum(
            1
            for term in ["trace", "risk", "test", "rollback", "evidence", "tradeoff", "privacy"]
            if term in answer_lower
        )
        raw_score = sum(item["score"] for item in rubric_scores)
        score = min(100, round((raw_score / max(1, len(rubric_scores))) * 75 + keyword_bonus * 4))
        return {
            "score": score,
            "status": "strong" if score >= 75 else "developing",
            "rubric": rubric_scores,
            "next_drill": "Repeat the scenario and make each rubric item explicit.",
        }

    def _preview_action(
        self,
        tool_name: str,
        title: str,
        inputs: dict[str, Any],
    ) -> str:
        if tool_name == "create_memory":
            source_title = inputs.get("source_title", title)
            return (
                "Atlas will create a new memory with title "
                f"'{inputs.get('title') or title}' and source '{source_title}'."
            )
        content = self._action_content(tool_name, title, inputs)
        return content[:1800]

    def _execute_action(self, action: ApprovalAction) -> tuple[dict[str, Any], str | None]:
        if action.tool_name == "create_memory":
            memory = self.create_memory(
                MemoryCreate(
                    source_title=str(action.inputs.get("source_title") or action.title),
                    source_type=str(action.inputs.get("source_type") or "approved action"),
                    memory_type=str(action.inputs.get("memory_type") or "decision"),
                    title=str(action.inputs.get("title") or action.title),
                    content=str(action.inputs.get("content") or action.preview),
                    tags=list(action.inputs.get("tags") or ["approved", "action"]),
                    importance=float(action.inputs.get("importance") or 0.7),
                    metadata={"approval_action_id": action.id},
                )
            )
            return {"memory_id": memory.id, "content": memory.content or ""}, None

        content = self._action_content(action.tool_name, action.title, action.inputs)
        artifact_path = self._write_artifact(action, content)
        return {"artifact_path": artifact_path, "content": content}, artifact_path

    def _action_content(self, tool_name: str, title: str, inputs: dict[str, Any]) -> str:
        profile = self.get_profile()
        journal_summary = self.summarize_journal()
        bullets = journal_summary.resume_bullets or [
            (
                "Built Atlas, a personal AI operating system that unifies memory, "
                "code intelligence, workflow automation, approval-gated tool execution, "
                "and traceable agent reasoning to assist with engineering work, learning, "
                "career planning, and daily productivity."
            )
        ]
        target = str(inputs.get("target") or inputs.get("target_role") or "AI engineering")
        topic = str(inputs.get("topic") or title)

        if tool_name == "create_markdown_report":
            sections = inputs.get("sections") or ["Summary", "Evidence", "Next Steps"]
            body = "\n\n".join(
                f"## {section}\n{self._report_section(str(section), target)}"
                for section in sections
            )
            return f"# {title}\n\nOwner: {profile.name or 'Atlas user'}\n\n{body}\n"
        if tool_name == "create_project_roadmap":
            return (
                f"# {title}\n\n"
                "## Outcomes\n"
                f"- Make Atlas stronger for {target}.\n"
                "- Keep every workflow traceable to source evidence.\n\n"
                "## Milestones\n"
                "- Ship one backend capability with tests.\n"
                "- Build the matching UI flow.\n"
                "- Run evals and record the result.\n"
                "- Convert the work into resume and interview artifacts.\n"
            )
        if tool_name == "create_task_list":
            tasks = inputs.get("tasks") or [
                "Run code intelligence on the latest repo.",
                "Review deterministic risk report.",
                "Create a journal entry for today.",
                "Generate a cited resume bullet.",
            ]
            return "# " + title + "\n\n" + "\n".join(f"- [ ] {task}" for task in tasks) + "\n"
        if tool_name == "export_resume_bullets":
            return "# Resume Bullets\n\n" + "\n".join(f"- {bullet}" for bullet in bullets) + "\n"
        if tool_name == "generate_interview_prep_doc":
            return (
                f"# {title}\n\n"
                f"Target: {target}\n\n"
                "## Pitch\n"
                "I built Atlas as a private, traceable personal AI OS for engineering work, "
                "learning, career planning, and daily productivity.\n\n"
                "## Stories\n"
                + "\n".join(f"- {story}" for story in journal_summary.interview_stories[:4])
                + "\n\n## Questions To Practice\n"
                "- How did you design memory and citations?\n"
                "- How do approval gates reduce risk?\n"
                "- How does code intelligence support AI workflows?\n"
            )
        if tool_name == "create_github_issue_draft":
            return (
                f"# GitHub Issue Draft: {topic}\n\n"
                "## Problem\n"
                f"{inputs.get('problem') or 'Atlas needs a focused implementation task.'}\n\n"
                "## Proposed Scope\n"
                f"{inputs.get('scope') or 'Implement the smallest traceable product slice.'}\n\n"
                "## Acceptance Criteria\n"
                "- Feature works locally.\n"
                "- Tests cover useful behavior.\n"
                "- Documentation reflects the change.\n"
            )
        if tool_name == "generate_auto_demo_pack":
            return (
                f"# {title}\n\n"
                "## README Section\n"
                "Atlas demonstrates local-first memory, code intelligence, knowledge graph, "
                "approval-gated tools, traces, and self-evaluation.\n\n"
                "## Demo Script\n"
                "1. Open Command Center.\n"
                "2. Show privacy permissions and memory export.\n"
                "3. Open Knowledge Graph and Growth Map.\n"
                "4. Run a simulator scenario and self-check the answer.\n"
                "5. Approve this demo pack artifact.\n\n"
                "## Resume Bullet\n"
                + "\n".join(f"- {bullet}" for bullet in bullets[:3])
                + "\n\n## LinkedIn Draft\n"
                "Built Atlas as a personal AI OS with memory, code intelligence, privacy "
                "controls, approval gates, and traceable reasoning.\n\n"
                "## Interview Pitch\n"
                "Atlas is a realistic AI product that connects personal context, codebase "
                "understanding, career workflows, and trustworthy action execution.\n"
            )
        return f"# {title}\n\nUnsupported tool name `{tool_name}` was previewed but not executed.\n"

    def _report_section(self, section: str, target: str) -> str:
        if section.lower() == "evidence":
            memories = self.list_memories()[:4]
            return "\n".join(
                f"- {memory.title or memory.source_title}: {memory.summary}" for memory in memories
            ) or "No memory evidence has been stored yet."
        if section.lower() == "next steps":
            return (
                f"- Prioritize the highest-leverage Atlas work for {target}.\n"
                "- Run a workflow and inspect its trace.\n"
                "- Capture the result as a cited career artifact."
            )
        return f"Atlas report section for {target}, grounded in current profile and memory."

    def _write_artifact(self, action: ApprovalAction, content: str) -> str:
        artifact_dir = _artifact_dir()
        artifact_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{action.created_at.strftime('%Y%m%d')}-{_slug(action.title)}.md"
        path = artifact_dir / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _latest_risk_metrics(self) -> dict[str, Any]:
        self.initialize()
        with self._connect() as db:
            row = db.execute(
                """
                select metrics from code_risk_reports
                order by datetime(generated_at) desc
                limit 1
                """
            ).fetchone()
        return decode_json(row["metrics"], {}) if row else {}

    def _score_eval(self, eval_id: str, signals: dict[str, bool]) -> float:
        requirements = {
            "resume_bullet_quality": ["has_memory", "has_citations"],
            "memory_retrieval_accuracy": ["has_memory", "has_citations"],
            "codebase_qa_correctness": ["has_repo", "has_code"],
            "workflow_reliability": ["has_traces"],
            "citation_quality": ["has_citations", "has_traces"],
            "hallucination_checks": ["has_memory", "has_traces"],
        }[eval_id]
        met = sum(1 for requirement in requirements if signals.get(requirement))
        return round(0.35 + (0.65 * met / len(requirements)), 2)

    def _eval_evidence(self, eval_id: str, signals: dict[str, bool]) -> list[str]:
        labels = {
            "has_memory": "memory rows exist",
            "has_citations": "stored memories include citations",
            "has_traces": "trace runs exist",
            "has_code": "code symbols exist",
            "has_repo": "repository is indexed",
            "has_approvals": "approval actions exist",
        }
        return [label for key, label in labels.items() if signals.get(key)] or [
            f"{eval_id} needs more local evidence"
        ]

    def _repo_from_row(self, row: sqlite3.Row) -> RepoProject:
        return RepoProject(
            id=row["id"],
            name=row["name"],
            origin_type=row["origin_type"],
            origin_url=row["origin_url"],
            status=row["status"],
            summary=row["summary"],
            language_stats=decode_json(row["language_stats"], {}),
            readme=row["readme"],
            dependency_files=decode_json(row["dependency_files"], []),
            file_tree=[RepoFile(**item) for item in decode_json(row["file_tree"], [])],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _repo_summary(
        self,
        name: str,
        files: list[RepoFile],
        language_stats: dict[str, int],
        dependency_files: list[str],
        readme: str | None,
    ) -> str:
        top_languages = ", ".join(
            language
            for language, _ in sorted(
                language_stats.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:4]
        )
        readme_signal = summarize_text(readme or "", max_chars=180)
        return (
            f"{name} contains {len(files)} indexed files. "
            f"Primary languages: {top_languages or 'unknown'}. "
            f"Dependency files: {', '.join(dependency_files[:5]) or 'none found'}. "
            f"README signal: {readme_signal or 'No README extracted.'}"
        )


settings = get_settings()
store = AtlasStore(settings.storage_path, settings.embedding_dimensions)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _artifact_dir() -> Path:
    configured = Path(settings.artifact_dir)
    if configured.is_absolute():
        return configured
    return _workspace_root() / configured


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72] or "atlas-artifact"


def _default_redaction_patterns() -> list[str]:
    return [
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",
        r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]+",
        r"\bsk-[A-Za-z0-9]{20,}\b",
    ]


def _skill_category(name: str) -> str:
    lower = name.lower()
    if any(term in lower for term in ["fastapi", "backend", "api", "python"]):
        return "Backend"
    if any(term in lower for term in ["agent", "llm", "retrieval", "pgvector", "openai"]):
        return "AI Agents"
    if any(term in lower for term in ["ml", "model", "embedding", "evaluation"]):
        return "ML Systems"
    if any(term in lower for term in ["postgres", "redis", "database", "sql"]):
        return "Databases"
    if any(term in lower for term in ["docker", "devops", "deploy", "kubernetes"]):
        return "DevOps"
    if any(term in lower for term in ["system design", "distributed"]):
        return "System Design"
    if any(term in lower for term in ["dsa", "algorithm", "data structure"]):
        return "DSA"
    if any(term in lower for term in ["communication", "interview", "writing", "resume"]):
        return "Communication"
    return "Engineering"


def _dependency_filenames() -> set[str]:
    return {
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "requirements.txt",
        "poetry.lock",
        "dockerfile",
        "docker-compose.yml",
        "go.mod",
        "cargo.toml",
        "pom.xml",
    }


def _strip_zip_root(path: str) -> str:
    clean = path.strip("/")
    parts = clean.split("/")
    if len(parts) > 1:
        return "/".join(parts[1:])
    return clean


def _ignored_repo_path(path: str) -> bool:
    ignored_parts = {".git", "node_modules", ".next", "__pycache__", ".venv", "dist", "build"}
    return any(part in ignored_parts for part in path.split("/"))


def _is_text_path(path: str) -> bool:
    return Path(path).suffix.lower() in {
        ".md",
        ".txt",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".json",
        ".toml",
        ".yml",
        ".yaml",
        ".css",
        ".html",
        ".go",
        ".rs",
        ".java",
    }


def _language_for_path(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".md": "Markdown",
        ".json": "JSON",
        ".css": "CSS",
        ".html": "HTML",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".sql": "SQL",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
    }.get(suffix)
