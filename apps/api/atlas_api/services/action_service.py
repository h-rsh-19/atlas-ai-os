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


class ActionService:
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


