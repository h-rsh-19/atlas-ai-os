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


class GrowthService:
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
        active_llm = settings.llm_provider.lower().strip()
        active_embedding = settings.embedding_provider.lower().strip()
        return [
            ModelProvider(
                id="openai",
                name="OpenAI-compatible cloud",
                mode="cloud",
                endpoint=settings.openai_base_url,
                status=(
                    "active"
                    if active_llm == "openai" or active_embedding == "openai"
                    else "configured"
                    if settings.openai_api_key
                    else "needs_key"
                ),
                notes=(
                    f"Chat model: {settings.openai_chat_model}. "
                    f"Embedding model: {settings.embedding_model}. "
                    "Uses ATLAS_OPENAI_API_KEY when selected."
                ),
            ),
            ModelProvider(
                id="deterministic",
                name="Deterministic local fallback",
                mode="local",
                endpoint=None,
                status="active" if active_llm == "deterministic" else "available",
                notes=(
                    "Offline test-safe generation and hash embeddings. "
                    "This is the default prototype mode."
                ),
            ),
            ModelProvider(
                id="ollama",
                name="Ollama",
                mode="local",
                endpoint=settings.ollama_base_url,
                status=(
                    "active"
                    if active_llm == "ollama" or active_embedding == "ollama"
                    else "available_if_running"
                ),
                notes=(
                    f"Chat model: {settings.ollama_model}. "
                    "Embeddings use ATLAS_EMBEDDING_MODEL when selected."
                ),
            ),
            ModelProvider(
                id="vllm",
                name="vLLM OpenAI-compatible server",
                mode="local",
                endpoint=settings.vllm_base_url,
                status=(
                    "active"
                    if active_llm == "vllm" or active_embedding == "vllm"
                    else "available_if_running"
                ),
                notes=(
                    f"Model: {settings.vllm_model}. "
                    "Uses OpenAI-compatible chat and embedding endpoints."
                ),
            ),
        ]


    def demo_flow_status(self) -> DemoFlowStatus:
        self.initialize()
        settings = get_settings()
        profile = self.get_profile()
        resume = self.latest_resume()
        memories = self.list_memories()
        repos = self.list_repos()
        analyzed_repos = [
            repo
            for repo in repos
            if self.get_code_graph(repo.id) is not None or self.get_code_risks(repo.id) is not None
        ]
        workflows = self.list_workflow_runs()
        actions = self.list_actions()
        artifacts = self.list_artifacts()
        traces = self.list_traces()
        chat_traces = [trace for trace in traces if trace.interaction_type == "chat"]
        approved_actions = [action for action in actions if action.status == "approved"]
        pending_actions = [action for action in actions if action.status == "pending"]

        def step(
            step_id: str,
            title: str,
            route: str,
            complete: bool,
            ready: bool,
            detail: str,
            evidence_count: int,
        ) -> DemoFlowStep:
            status = "completed" if complete else "ready" if ready else "pending"
            return DemoFlowStep(
                id=step_id,
                title=title,
                route=route,
                status=status,
                detail=detail,
                evidence_count=evidence_count,
            )

        steps = [
            step(
                "resume_upload",
                "Upload resume and extract evidence",
                "/resume",
                resume is not None,
                True,
                (
                    f"Latest resume parsed from {resume.filename}."
                    if resume
                    else "Upload a PDF resume so Atlas can create source-backed career memory."
                ),
                1 if resume else 0,
            ),
            step(
                "profile_goals",
                "Confirm profile, goals, and target roles",
                "/profile",
                bool(profile.name and profile.current_goals and profile.target_roles),
                resume is not None or bool(memories),
                (
                    f"{profile.name or 'Profile'} targeting {', '.join(profile.target_roles[:2])}."
                    if profile.target_roles
                    else "Add name, current goals, target roles, skills, and weak areas."
                ),
                len(profile.current_goals) + len(profile.target_roles),
            ),
            step(
                "memory_retrieval",
                "Ask a grounded memory question",
                "/memory",
                bool(chat_traces and memories),
                bool(memories),
                (
                    f"{len(memories)} memories available and "
                    f"{len(chat_traces)} chat traces recorded."
                    if memories
                    else "Create resume/project/note memories before testing grounded chat."
                ),
                len(memories),
            ),
            step(
                "repo_upload",
                "Upload or connect a repository",
                "/projects",
                bool(repos),
                True,
                (
                    f"{len(repos)} repository project(s) indexed."
                    if repos
                    else "Upload a local ZIP or add a GitHub URL to create code evidence."
                ),
                len(repos),
            ),
            step(
                "code_analysis",
                "Run code analysis and inspect risks",
                "/code",
                bool(analyzed_repos),
                bool(repos),
                (
                    f"{len(analyzed_repos)} repository project(s) have graph/risk analysis."
                    if analyzed_repos
                    else "Run analysis on an indexed repo to populate symbols, graph, and risks."
                ),
                len(analyzed_repos),
            ),
            step(
                "workflow",
                "Run a context-aware workflow",
                "/workflows",
                bool(workflows),
                bool(memories),
                (
                    f"{len(workflows)} workflow run(s) recorded."
                    if workflows
                    else "Run resume bullets, learning plan, interview prep, or repo workflow."
                ),
                len(workflows),
            ),
            step(
                "approval",
                "Preview and approve an action",
                "/actions",
                bool(approved_actions),
                bool(pending_actions or workflows),
                (
                    f"{len(approved_actions)} approved action(s), {len(pending_actions)} pending."
                    if actions
                    else "Propose an artifact action and approve it from the action queue."
                ),
                len(actions),
            ),
            step(
                "artifact_trace",
                "Open the generated artifact and trace",
                "/traces",
                bool(artifacts and traces),
                bool(approved_actions or workflows or chat_traces),
                (
                    f"{len(artifacts)} artifact(s) and {len(traces)} trace(s) available."
                    if traces
                    else "Complete a chat, workflow, or action to inspect trace evidence."
                ),
                len(artifacts) + len(traces),
            ),
        ]
        completed = sum(1 for item in steps if item.status == "completed")
        next_step = next(
            (item.title for item in steps if item.status != "completed"),
            "Demo flow complete. Start with the trace viewer for the recruiter story.",
        )
        return DemoFlowStatus(
            title="Golden Atlas Demo Flow",
            current_mode=(
                "local deterministic prototype with LLM-ready architecture "
                f"(generation={settings.llm_provider}, embeddings={settings.embedding_provider})"
            ),
            completion_percent=round((completed / len(steps)) * 100),
            next_step=next_step,
            steps=steps,
            artifact=self.demo_artifact_summary(),
            resume_bullet=self.demo_resume_bullet(),
        )
