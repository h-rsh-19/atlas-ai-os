from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from atlas_api.core.config import get_settings
from atlas_api.schemas import (
    ApprovalAction,
    ArtifactRecord,
    Citation,
    CodeGraph,
    CodeRiskItem,
    CodeRiskReport,
    CodeSymbol,
    DashboardSummary,
    DecisionCreate,
    DecisionEntry,
    EvaluationPrompt,
    EvaluationRun,
    JournalEntry,
    JournalEntryCreate,
    JournalSummary,
    MemoryItem,
    PluginManifest,
    PrivacySettings,
    RepoFile,
    RepoProject,
    ResumeProfile,
    ResumeStructuredProfile,
    RetrievalHit,
    SimulationRun,
    SimulatorScenario,
    SourceDocument,
    TraceRun,
    TraceStep,
    UserProfile,
    UserProfileUpdate,
    WorkflowRunDetail,
)
from atlas_api.services.action_service import ActionService
from atlas_api.services.chunking import chunk_text, summarize_text
from atlas_api.services.code_service import CodeService
from atlas_api.services.demo_service import DemoService
from atlas_api.services.embeddings import get_embedding_provider
from atlas_api.services.growth_service import GrowthService
from atlas_api.services.llm import get_llm_provider
from atlas_api.services.memory_service import MemoryService
from atlas_api.services.privacy_service import PrivacyService
from atlas_api.services.resume_parser import StructuredResume
from atlas_api.services.trace_service import TraceService
from atlas_api.services.workflow_service import WorkflowService


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


class AtlasStore(
    MemoryService,
    TraceService,
    WorkflowService,
    CodeService,
    DemoService,
    ActionService,
    PrivacyService,
    GrowthService,
):
    def __init__(self, path: str, embedding_dimensions: int) -> None:
        self.path = path
        self.embedding_dimensions = embedding_dimensions
        settings = get_settings()
        self.embedding_provider = get_embedding_provider(settings)
        self.llm_provider = get_llm_provider(settings)
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

                    create table if not exists demo_ownership (
                        id text primary key,
                        demo_run_id text not null,
                        entity_type text not null,
                        entity_id text not null,
                        metadata text not null,
                        created_at text not null
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
                    create index if not exists ix_demo_ownership_run
                        on demo_ownership(demo_run_id);
                    create index if not exists ix_demo_ownership_entity
                        on demo_ownership(entity_type, entity_id);
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
        embedding_result = self.embedding_provider.embed(f"{title}\n{content}")
        embedding = embedding_result.vector
        source = db.execute("select * from source_documents where id = ?", (source_id,)).fetchone()
        citation = {
            "source_id": source_id,
            "title": source["title"] if source else title,
            "uri": source["uri"] if source else None,
            "snippet": summarize_text(content, max_chars=180),
        }
        metadata_with_embedding = dict(metadata)
        metadata_with_embedding["_embedding"] = embedding
        metadata_with_embedding["_embedding_provider"] = embedding_result.provider
        metadata_with_embedding["_embedding_model"] = embedding_result.model
        metadata_with_embedding["_embedding_dimensions"] = embedding_result.dimensions
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
