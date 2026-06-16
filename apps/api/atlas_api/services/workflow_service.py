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
from atlas_api.services.llm import WorkflowJsonOutput, workflow_template
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


class WorkflowService:
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

        deterministic_outputs = self._workflow_output(
            workflow_name, inputs, profile, hits, journals
        )
        llm_result = self.llm_provider.generate_json(
            template=workflow_template(),
            variables={
                "workflow_name": workflow_name,
                "inputs": inputs,
                "profile": profile.model_dump(mode="json"),
                "evidence": [hit.model_dump(mode="json") for hit in hits],
                "fallback": deterministic_outputs,
            },
            fallback=deterministic_outputs,
            output_model=WorkflowJsonOutput,
        )
        outputs = llm_result.content
        outputs.setdefault("_provider", llm_result.provider)
        outputs.setdefault("_model", llm_result.model)
        outputs.setdefault("_fallback_used", llm_result.fallback_used)
        steps.append(
            TraceStep(
                name="compose_output",
                status="completed",
                output={
                    "keys": list(outputs.keys()),
                    "provider": llm_result.provider,
                    "model": llm_result.model,
                    "fallback_used": llm_result.fallback_used,
                },
                latency_ms=7,
            )
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        assumptions = [
            "Outputs are grounded in current stored profile, memories, resume, and journals.",
        ]
        if llm_result.fallback_used:
            assumptions.append("Deterministic workflow draft was used as provider fallback.")
        assumptions.extend(llm_result.errors)
        trace = self.create_trace(
            interaction_type=f"workflow:{workflow_name}",
            user_input=encode_json(inputs),
            retrieved_memories=hits,
            prompt_version=llm_result.prompt_version,
            model_used=f"{llm_result.provider}:{llm_result.model}",
            tool_calls=[{"tool": "memory.search"}, {"tool": "journal.list"}],
            generated_output=outputs,
            latency_ms=latency_ms,
            errors=llm_result.errors,
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
