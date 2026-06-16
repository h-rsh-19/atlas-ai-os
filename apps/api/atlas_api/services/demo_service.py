from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from atlas_api.schemas import (
    ApprovalActionCreate,
    DecisionCreate,
    DemoArtifactSummary,
    DemoResetResponse,
    DemoRunStepResponse,
    DemoScriptResponse,
    DemoSeedResponse,
    JournalEntryCreate,
    TraceStep,
    UserProfile,
    UserProfileUpdate,
)
from atlas_api.services.resume_parser import StructuredResume
from atlas_api.services.store_shared import decode_json, encode_json, new_id, now

DEMO_RESUME_FILENAME = "atlas-demo-resume.pdf"
DEMO_REPO_FILENAME = "atlas-demo-repo.zip"
DEMO_ACTION_TITLE = "Atlas auto-demo pack"
DEMO_PROFILE_NAME = "Atlas Demo Builder"
DEMO_STEP_ORDER = [
    "resume_upload",
    "profile_goals",
    "memory_retrieval",
    "repo_upload",
    "code_analysis",
    "workflow",
    "approval",
    "artifact_trace",
]


class DemoService:
    def seed_demo_state(self) -> DemoSeedResponse:
        self.initialize()
        reset = self.reset_demo_state()
        demo_run_id = new_id("demo")
        created: list[str] = []

        for step_id in DEMO_STEP_ORDER:
            created.extend(self._run_demo_step(step_id, demo_run_id))

        return DemoSeedResponse(
            message=(
                "Seeded Atlas demo state. "
                f"Reset removed {sum(reset.deleted.values())} rows first."
            ),
            created=created,
            flow=self.demo_flow_status(),
        )

    def run_next_demo_step(self) -> DemoRunStepResponse:
        self.initialize()
        flow = self.demo_flow_status()
        next_step = next((step for step in flow.steps if step.status != "completed"), None)
        if next_step is None:
            return DemoRunStepResponse(
                message="Demo flow is already complete.",
                ran_step=None,
                created=[],
                flow=flow,
            )

        demo_run_id = self._active_demo_run_id() or new_id("demo")
        created = self._run_demo_step(next_step.id, demo_run_id)
        return DemoRunStepResponse(
            message=f"Ran demo step: {next_step.title}.",
            ran_step=next_step.id,
            created=created,
            flow=self.demo_flow_status(),
        )

    def reset_demo_state(self) -> DemoResetResponse:
        self.initialize()
        deleted: dict[str, int] = {}
        artifact_paths: list[str] = []
        with self._lock, self._connect() as db:
            ownership_rows = db.execute(
                "select * from demo_ownership order by datetime(created_at) desc"
            ).fetchall()
            entities: dict[str, list[str]] = {}
            metadata_by_entity: dict[tuple[str, str], dict[str, Any]] = {}
            for row in ownership_rows:
                entity_type = row["entity_type"]
                entity_id = row["entity_id"]
                if entity_id not in entities.setdefault(entity_type, []):
                    entities[entity_type].append(entity_id)
                metadata_by_entity[(entity_type, entity_id)] = decode_json(row["metadata"], {})

            action_ids = entities.get("action", [])
            artifact_ids = entities.get("artifact", [])
            repo_ids = entities.get("repo", [])
            source_ids = entities.get("source", [])
            memory_ids = entities.get("memory", [])
            profile_ids = entities.get("profile", [])

            if action_ids:
                action_rows = self._select_ids(db, "approval_actions", action_ids)
                artifact_paths.extend(
                    row["artifact_path"] for row in action_rows if row["artifact_path"]
                )
                for row in action_rows:
                    if row["trace_id"] and row["trace_id"] not in entities.setdefault("trace", []):
                        entities["trace"].append(row["trace_id"])

                linked_artifact_rows = self._select_by_column(
                    db,
                    "artifact_records",
                    "action_id",
                    action_ids,
                )
                artifact_paths.extend(row["path"] for row in linked_artifact_rows if row["path"])
                deleted["artifact_records"] = self._delete_by_column(
                    db,
                    "artifact_records",
                    "action_id",
                    action_ids,
                )

            if artifact_ids:
                artifact_rows = self._select_ids(db, "artifact_records", artifact_ids)
                artifact_paths.extend(row["path"] for row in artifact_rows if row["path"])

            deleted["artifact_records"] = deleted.get("artifact_records", 0) + self._delete_ids(
                db,
                "artifact_records",
                artifact_ids,
            )
            deleted["approval_actions"] = self._delete_ids(db, "approval_actions", action_ids)
            deleted["workflow_runs"] = self._delete_ids(
                db,
                "workflow_runs_local",
                entities.get("workflow", []),
            )
            deleted["trace_runs"] = self._delete_ids(db, "trace_runs", entities.get("trace", []))

            if repo_ids:
                deleted["code_symbols"] = self._delete_by_column(
                    db,
                    "code_symbols",
                    "project_id",
                    repo_ids,
                )
                deleted["code_graphs"] = self._delete_by_column(
                    db,
                    "code_graphs",
                    "project_id",
                    repo_ids,
                )
                deleted["code_risks"] = self._delete_by_column(
                    db,
                    "code_risk_reports",
                    "project_id",
                    repo_ids,
                )
                deleted["repo_projects"] = self._delete_ids(db, "repo_projects", repo_ids)

            deleted["decision_entries"] = self._delete_ids(
                db,
                "decision_entries",
                entities.get("decision", []),
            )
            deleted["journal_entries"] = self._delete_ids(
                db,
                "journal_entries",
                entities.get("journal", []),
            )
            deleted["resume_profiles"] = self._delete_ids(
                db,
                "resume_profiles",
                entities.get("resume", []),
            )
            deleted["memories"] = self._delete_ids(db, "memories", memory_ids)
            deleted["source_documents"] = self._delete_ids(db, "source_documents", source_ids)

            if "default" in profile_ids:
                metadata = metadata_by_entity.get(("profile", "default"), {})
                previous = metadata.get("previous")
                if isinstance(previous, dict):
                    self._restore_profile(db, UserProfile(**previous))
                else:
                    self._restore_profile(
                        db,
                        UserProfile(
                            id="default",
                            name="",
                            role="Student / Developer",
                            current_goals=[],
                            target_roles=[],
                            skills=[],
                            weaknesses=[],
                            preferred_tech_stack=[],
                            learning_priorities=[
                                "Build Atlas",
                                "Practice interviews",
                                "Ship projects",
                            ],
                            updated_at=now(),
                        ),
                    )
                deleted["profile_reset"] = 1

            deleted["demo_ownership"] = db.execute("delete from demo_ownership").rowcount
            db.commit()

        for path_value in artifact_paths:
            path = Path(path_value)
            try:
                if path.exists() and path.is_file():
                    path.unlink()
            except OSError:
                pass

        return DemoResetResponse(
            message="Reset Atlas demo-owned state.",
            deleted={key: value for key, value in deleted.items() if value},
            flow=self.demo_flow_status(),
        )

    def demo_artifact_summary(self) -> DemoArtifactSummary | None:
        artifact = self._latest_demo_artifact()
        if artifact is None:
            return None
        return DemoArtifactSummary(
            id=artifact.id,
            action_id=artifact.action_id,
            title=artifact.title,
            path=artifact.path,
            content_preview=artifact.content_preview,
        )

    def demo_resume_bullet(self) -> str | None:
        artifact = self._latest_demo_artifact()
        if artifact is not None:
            content = self._artifact_content(artifact.path)
            bullet = self._extract_resume_bullet(content)
            if bullet and "Demo seed:" not in bullet:
                return bullet
        return (
            "Built Atlas, a personal AI operating system that unifies memory, "
            "code intelligence, workflow automation, approval-gated tool execution, "
            "and traceable agent reasoning to assist with engineering work, learning, "
            "career planning, and daily productivity."
        )

    def recruiter_demo_script(self) -> DemoScriptResponse:
        flow = self.demo_flow_status()
        blockers = [step for step in flow.steps if step.status != "completed"]
        blocker_text = (
            "Demo blockers: " + "; ".join(step.title for step in blockers)
            if blockers
            else "Demo flow is complete."
        )
        script = "\n".join(
            [
                "Atlas recruiter demo script",
                "",
                f"Mode: {flow.current_mode}",
                f"Progress: {flow.completion_percent}%",
                blocker_text,
                "",
                "1. Start on /demo and show the single golden path.",
                "2. Open resume/profile evidence and explain that memory is source-backed.",
                "3. Ask a grounded question and show citations plus provider state.",
                "4. Open the demo repo analysis and show symbols, risks, and graph evidence.",
                "5. Run a workflow and show structured output plus trace linkage.",
                "6. Open Actions and show approval-gated artifact generation.",
                "7. Open Traces and show evidence, prompt version, tools, output, "
                "errors, and latency.",
                "",
                "Close: Atlas is a local deterministic prototype with LLM-ready architecture, "
                "built around trust, evidence, approvals, and engineering usefulness.",
            ]
        )
        return DemoScriptResponse(script=script)

    def _run_demo_step(self, step_id: str, demo_run_id: str) -> list[str]:
        if step_id == "resume_upload":
            return self._seed_demo_resume(demo_run_id)
        if step_id == "profile_goals":
            return [
                *self._seed_demo_profile(demo_run_id),
                *self._seed_demo_journal(demo_run_id),
                *self._seed_demo_decision(demo_run_id),
            ]
        if step_id == "memory_retrieval":
            return self._seed_demo_chat_trace(demo_run_id)
        if step_id == "repo_upload":
            return self._seed_demo_repo(demo_run_id)
        if step_id == "code_analysis":
            return self._seed_demo_code_analysis(demo_run_id)
        if step_id == "workflow":
            return self._seed_demo_workflow(demo_run_id)
        if step_id in {"approval", "artifact_trace"}:
            return self._seed_demo_action(demo_run_id)
        return []

    def _seed_demo_profile(self, demo_run_id: str) -> list[str]:
        existing = self.get_profile()
        self._record_demo_entity(
            demo_run_id,
            "profile",
            "default",
            metadata={"previous": existing.model_dump(mode="json")},
        )
        self.update_profile(
            UserProfileUpdate(
                name=DEMO_PROFILE_NAME,
                role="Student Developer / AI Product Engineer",
                current_goals=[
                    "Turn Atlas into a recruiter-grade AI systems project",
                    "Build traceable workflows with approvals and evaluations",
                ],
                target_roles=["AI Product Engineer", "Backend AI Engineer"],
                skills=["Python", "FastAPI", "TypeScript", "React", "PostgreSQL"],
                weaknesses=[
                    "Distributed systems depth",
                    "Production incident storytelling",
                ],
                preferred_tech_stack=[
                    "Next.js",
                    "FastAPI",
                    "PostgreSQL",
                    "Redis",
                    "Docker",
                ],
                learning_priorities=[
                    "provider reliability",
                    "retrieval evaluation",
                    "code intelligence",
                ],
            )
        )
        return ["profile"]

    def _seed_demo_resume(self, demo_run_id: str) -> list[str]:
        resume_text = "\n".join(
            [
                "Education",
                "B.S. Computer Science, systems and AI focus",
                "Projects",
                "Atlas personal AI OS with memory, provider fallback, approvals, "
                "traces, and code intelligence",
                "Experience",
                "Built full-stack AI workflow prototypes with FastAPI, Next.js, and PostgreSQL",
                "Skills",
                "Python, FastAPI, TypeScript, React, PostgreSQL, Redis, Docker, OpenAI, pgvector",
                "Achievements",
                "Shipped a traceable AI product demo with validation, tests, "
                "and approval-gated actions",
            ]
        )
        resume, memories = self.store_resume(
            filename=DEMO_RESUME_FILENAME,
            raw_text=resume_text,
            structured=StructuredResume(
                education=["B.S. Computer Science, systems and AI focus"],
                experience=[
                    "Built full-stack AI workflow prototypes with FastAPI, Next.js, and PostgreSQL"
                ],
                projects=[
                    "Atlas personal AI OS with memory, provider fallback, approvals, "
                    "traces, and code intelligence"
                ],
                skills=[
                    "Python",
                    "FastAPI",
                    "TypeScript",
                    "React",
                    "PostgreSQL",
                    "Redis",
                    "Docker",
                    "OpenAI",
                    "pgvector",
                ],
                achievements=[
                    "Shipped a traceable AI product demo with validation, tests, "
                    "and approval-gated actions"
                ],
            ),
        )
        self._record_demo_entity(demo_run_id, "resume", resume.id)
        self._record_demo_entity(demo_run_id, "source", resume.source_id)
        for memory in memories:
            self._record_demo_entity(demo_run_id, "memory", memory.id)
        return [f"resume:{resume.id}", f"memories:{len(memories)}"]

    def _seed_demo_journal(self, demo_run_id: str) -> list[str]:
        journal = self.create_journal_entry(
            JournalEntryCreate(
                built=(
                    "Demo seed: wired Atlas demo flow, provider validation, "
                    "and trace visibility."
                ),
                problems=(
                    "Needed a single story that proves memory, code, workflow, "
                    "approval, and trace."
                ),
                decisions="Seed only demo-owned data and keep reset scoped.",
                skills_used=["FastAPI", "Next.js", "Product engineering"],
                next_tasks=[
                    "Capture screenshots",
                    "Add migrations",
                    "Add provider health checks",
                ],
            )
        )
        self._record_demo_entity(demo_run_id, "journal", journal.id)
        self._record_demo_source_and_memories_by_uri(demo_run_id, f"journal://{journal.id}")
        return [f"journal:{journal.id}"]

    def _seed_demo_decision(self, demo_run_id: str) -> list[str]:
        decision = self.create_decision(
            DecisionCreate(
                title="Demo seed: deterministic fallback with visible provider status",
                decision=(
                    "Use deterministic mode by default, but show provider failures "
                    "when fallback occurs."
                ),
                alternatives=["Silent fallback", "Hard fail on provider errors"],
                tradeoffs=[
                    "Demo stays reliable",
                    "Serious testing can disable fallback later",
                ],
                reason=(
                    "Atlas should be useful offline without hiding provider reliability issues."
                ),
                tags=["demo_seed", "provider", "trace"],
            )
        )
        self._record_demo_entity(demo_run_id, "decision", decision.id)
        if decision.memory_id:
            self._record_demo_entity(demo_run_id, "memory", decision.memory_id)
            self._record_source_for_memory(demo_run_id, decision.memory_id)
        return [f"decision:{decision.id}"]

    def _seed_demo_repo(self, demo_run_id: str) -> list[str]:
        repo = self.ingest_repo_zip(DEMO_REPO_FILENAME, _demo_repo_zip())
        self._record_demo_entity(demo_run_id, "repo", repo.id)
        return [f"repo:{repo.id}"]

    def _seed_demo_code_analysis(self, demo_run_id: str) -> list[str]:
        repo = self._latest_demo_repo() or self.ingest_repo_zip(
            DEMO_REPO_FILENAME,
            _demo_repo_zip(),
        )
        self._record_demo_entity(demo_run_id, "repo", repo.id)
        self.analyze_codebase(repo.id)
        return [f"code_analysis:{repo.id}"]

    def _seed_demo_chat_trace(self, demo_run_id: str) -> list[str]:
        hits = self.search_memories("What should I learn next for Atlas?", top_k=5)
        trace = self.create_trace(
            interaction_type="chat",
            user_input="What should I learn next for Atlas?",
            retrieved_memories=hits,
            prompt_version="demo-seed-chat-v1",
            model_used="deterministic:atlas-deterministic-v1",
            tool_calls=[{"tool": "memory.search", "demo_seed": True}],
            generated_output={
                "answer": (
                    "Focus on provider reliability, retrieval evaluation, "
                    "and code intelligence."
                ),
                "demo_seed": True,
                "fallback_used": False,
            },
            latency_ms=4,
            confidence=0.82,
            assumptions=["Seeded demo trace created from local memory evidence."],
            steps=[
                TraceStep(
                    name="retrieve_memory",
                    status="completed",
                    output={"hits": len(hits), "demo_seed": True},
                    latency_ms=2,
                )
            ],
        )
        self._record_demo_entity(demo_run_id, "trace", trace.id)
        return [f"chat_trace:{trace.id}"]

    def _seed_demo_workflow(self, demo_run_id: str) -> list[str]:
        workflow = self.run_workflow(
            "generate_resume_bullets",
            {"target_role": "AI Product Engineer", "project": "Atlas", "demo_seed": True},
        )
        self._record_demo_entity(demo_run_id, "workflow", workflow.id)
        if workflow.trace_id:
            self._record_demo_entity(demo_run_id, "trace", workflow.trace_id)
        return [f"workflow:{workflow.id}"]

    def _seed_demo_action(self, demo_run_id: str) -> list[str]:
        existing = self._latest_demo_artifact()
        if existing is not None:
            self._record_demo_entity(demo_run_id, "artifact", existing.id)
            self._record_demo_entity(demo_run_id, "action", existing.action_id)
            action = self.get_action(existing.action_id)
            if action and action.trace_id:
                self._record_demo_entity(demo_run_id, "trace", action.trace_id)
            return [f"artifact:{existing.id}"]

        action = self.propose_action(
            ApprovalActionCreate(
                tool_name="generate_auto_demo_pack",
                title=DEMO_ACTION_TITLE,
                risk_level="medium",
                inputs={
                    "target": "Atlas recruiter demo",
                    "sections": [
                        "README section",
                        "demo script",
                        "resume bullet",
                        "interview pitch",
                    ],
                    "demo_seed": True,
                },
            )
        )
        self._record_demo_entity(demo_run_id, "action", action.id)
        approved = self.approve_action(action.id)
        created = [f"artifact_action:{action.id}"]
        if approved:
            self._record_demo_entity(demo_run_id, "action", approved.id)
            if approved.trace_id:
                self._record_demo_entity(demo_run_id, "trace", approved.trace_id)
            artifact = self._artifact_for_action(approved.id)
            if artifact is not None:
                self._record_demo_entity(demo_run_id, "artifact", artifact.id)
                created.append(f"artifact:{artifact.id}")
        return created

    def _record_demo_entity(
        self,
        demo_run_id: str,
        entity_type: str,
        entity_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock, self._connect() as db:
            db.execute(
                """
                insert or replace into demo_ownership (
                    id, demo_run_id, entity_type, entity_id, metadata, created_at
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{demo_run_id}:{entity_type}:{entity_id}",
                    demo_run_id,
                    entity_type,
                    entity_id,
                    encode_json(metadata or {}),
                    now().isoformat(),
                ),
            )
            db.commit()

    def _record_demo_source_and_memories_by_uri(self, demo_run_id: str, uri: str) -> None:
        with self._connect() as db:
            source = db.execute("select id from source_documents where uri = ?", (uri,)).fetchone()
            if not source:
                return
            memory_rows = db.execute(
                "select id from memories where source_id = ?",
                (source["id"],),
            ).fetchall()
        self._record_demo_entity(demo_run_id, "source", source["id"])
        for row in memory_rows:
            self._record_demo_entity(demo_run_id, "memory", row["id"])

    def _record_source_for_memory(self, demo_run_id: str, memory_id: str) -> None:
        with self._connect() as db:
            row = db.execute(
                "select source_id from memories where id = ?",
                (memory_id,),
            ).fetchone()
        if row and row["source_id"]:
            self._record_demo_entity(demo_run_id, "source", row["source_id"])

    def _active_demo_run_id(self) -> str | None:
        with self._connect() as db:
            row = db.execute(
                """
                select demo_run_id from demo_ownership
                order by datetime(created_at) desc
                limit 1
                """
            ).fetchone()
        return str(row["demo_run_id"]) if row else None

    def _latest_demo_repo(self) -> Any | None:
        with self._connect() as db:
            row = db.execute(
                """
                select * from repo_projects
                where id in (
                    select entity_id from demo_ownership where entity_type = 'repo'
                )
                order by datetime(created_at) desc
                limit 1
                """
            ).fetchone()
            if row is None:
                row = db.execute(
                    """
                    select * from repo_projects
                    where origin_url = ?
                    order by datetime(created_at) desc
                    limit 1
                    """,
                    (DEMO_REPO_FILENAME,),
                ).fetchone()
        return self._repo_from_row(row) if row else None

    def _latest_demo_artifact(self) -> Any | None:
        with self._connect() as db:
            row = db.execute(
                """
                select * from artifact_records
                where id in (
                    select entity_id from demo_ownership where entity_type = 'artifact'
                )
                order by datetime(created_at) desc
                limit 1
                """
            ).fetchone()
            if row is None:
                row = db.execute(
                    """
                    select artifact_records.* from artifact_records
                    join approval_actions on approval_actions.id = artifact_records.action_id
                    where approval_actions.title = ?
                    order by datetime(artifact_records.created_at) desc
                    limit 1
                    """,
                    (DEMO_ACTION_TITLE,),
                ).fetchone()
        return self._artifact_from_row(row) if row else None

    def _artifact_for_action(self, action_id: str) -> Any | None:
        with self._connect() as db:
            row = db.execute(
                "select * from artifact_records where action_id = ?",
                (action_id,),
            ).fetchone()
        return self._artifact_from_row(row) if row else None

    def _artifact_content(self, path_value: str) -> str:
        path = Path(path_value)
        try:
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8")
        except OSError:
            return ""
        return ""

    def _extract_resume_bullet(self, content: str) -> str | None:
        in_section = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                in_section = line.lower() == "## resume bullet"
                continue
            if in_section and line.startswith("- "):
                return line[2:].strip()
        return None

    def _restore_profile(self, db: Any, profile: UserProfile) -> None:
        db.execute(
            """
            update user_profiles
            set name = ?, role = ?, current_goals = ?, target_roles = ?,
                skills = ?, weaknesses = ?, preferred_tech_stack = ?,
                learning_priorities = ?, updated_at = ?
            where id = 'default'
            """,
            (
                profile.name,
                profile.role,
                encode_json(profile.current_goals),
                encode_json(profile.target_roles),
                encode_json(profile.skills),
                encode_json(profile.weaknesses),
                encode_json(profile.preferred_tech_stack),
                encode_json(profile.learning_priorities),
                (
                    profile.updated_at.isoformat()
                    if profile.updated_at is not None
                    else now().isoformat()
                ),
            ),
        )

    def _select_ids(self, db: Any, table: str, ids: list[str]) -> list[Any]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        return db.execute(f"select * from {table} where id in ({placeholders})", ids).fetchall()

    def _select_by_column(
        self,
        db: Any,
        table: str,
        column: str,
        values: list[str],
    ) -> list[Any]:
        if not values:
            return []
        placeholders = ",".join("?" for _ in values)
        return db.execute(
            f"select * from {table} where {column} in ({placeholders})",
            values,
        ).fetchall()

    def _delete_ids(self, db: Any, table: str, ids: list[str]) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        return db.execute(f"delete from {table} where id in ({placeholders})", ids).rowcount

    def _delete_by_column(self, db: Any, table: str, column: str, values: list[str]) -> int:
        if not values:
            return 0
        placeholders = ",".join("?" for _ in values)
        return db.execute(
            f"delete from {table} where {column} in ({placeholders})",
            values,
        ).rowcount


def _demo_repo_zip() -> bytes:
    files = {
        "atlas-demo/README.md": "# Atlas Demo\n\nTraceable personal AI OS demo repository.",
        "atlas-demo/apps/api/main.py": (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n\n"
            "def plan_workflow(goal: str) -> list[str]:\n"
            "    return [\n"
            "        'retrieve evidence', 'generate output',\n"
            "        'self-check', 'request approval'\n"
            "    ]\n"
        ),
        "atlas-demo/apps/web/page.tsx": (
            "export default function Page() {\n"
            "  return <main>Atlas guided demo</main>;\n"
            "}\n"
        ),
        "atlas-demo/package.json": '{"dependencies":{"next":"16.2.9","react":"19.2.1"}}',
        "atlas-demo/pyproject.toml": '[project]\nname = "atlas-demo"\n',
        "atlas-demo/tests/test_main.py": "def test_demo():\n    assert True\n",
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()
