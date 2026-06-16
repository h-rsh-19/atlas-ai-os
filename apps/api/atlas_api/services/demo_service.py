from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from atlas_api.schemas import (
    ApprovalActionCreate,
    DecisionCreate,
    DemoResetResponse,
    DemoScriptResponse,
    DemoSeedResponse,
    JournalEntryCreate,
    TraceStep,
    UserProfileUpdate,
)
from atlas_api.services.resume_parser import StructuredResume
from atlas_api.services.store_shared import encode_json, now

DEMO_RESUME_FILENAME = "atlas-demo-resume.pdf"
DEMO_REPO_FILENAME = "atlas-demo-repo.zip"
DEMO_ACTION_TITLE = "Atlas auto-demo pack"


class DemoService:
    def seed_demo_state(self) -> DemoSeedResponse:
        self.initialize()
        reset = self.reset_demo_state()
        created: list[str] = []

        self.update_profile(
            UserProfileUpdate(
                name="Atlas Demo Builder",
                role="Student Developer / AI Product Engineer",
                current_goals=[
                    "Turn Atlas into a recruiter-grade AI systems project",
                    "Build traceable workflows with approvals and evaluations",
                ],
                target_roles=["AI Product Engineer", "Backend AI Engineer"],
                skills=["Python", "FastAPI", "TypeScript", "React", "PostgreSQL"],
                weaknesses=["Distributed systems depth", "Production incident storytelling"],
                preferred_tech_stack=["Next.js", "FastAPI", "PostgreSQL", "Redis", "Docker"],
                learning_priorities=[
                    "provider reliability",
                    "retrieval evaluation",
                    "code intelligence",
                ],
            )
        )
        created.append("profile")

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
        self.store_resume(
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
        created.append("resume")

        self.create_journal_entry(
            JournalEntryCreate(
                built=(
                    "Demo seed: wired Atlas demo flow, provider validation, "
                    "and trace visibility."
                ),
                problems=(
                    "Needed a single story that proves memory, code, workflow, approval, and trace."
                ),
                decisions="Seed only demo-owned data and keep reset scoped.",
                skills_used=["FastAPI", "Next.js", "Product engineering"],
                next_tasks=["Capture screenshots", "Add migrations", "Add provider health checks"],
            )
        )
        created.append("journal")

        decision = self.create_decision(
            DecisionCreate(
                title="Demo seed: deterministic fallback with visible provider status",
                decision=(
                    "Use deterministic mode by default, but show provider failures "
                    "when fallback occurs."
                ),
                alternatives=["Silent fallback", "Hard fail on provider errors"],
                tradeoffs=["Demo stays reliable", "Serious testing can disable fallback later"],
                reason="Atlas should be useful offline without hiding provider reliability issues.",
                tags=["demo_seed", "provider", "trace"],
            )
        )
        created.append(f"decision:{decision.id}")

        repo = self.ingest_repo_zip(DEMO_REPO_FILENAME, _demo_repo_zip())
        self.analyze_codebase(repo.id)
        created.append(f"repo:{repo.id}")

        hits = self.search_memories("What should I learn next for Atlas?", top_k=5)
        self.create_trace(
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
        created.append("chat_trace")

        workflow = self.run_workflow(
            "generate_resume_bullets",
            {"target_role": "AI Product Engineer", "project": "Atlas", "demo_seed": True},
        )
        created.append(f"workflow:{workflow.id}")

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
        self.approve_action(action.id)
        created.append(f"artifact_action:{action.id}")

        return DemoSeedResponse(
            message=(
                "Seeded Atlas demo state. "
                f"Reset removed {sum(reset.deleted.values())} rows first."
            ),
            created=created,
            flow=self.demo_flow_status(),
        )

    def reset_demo_state(self) -> DemoResetResponse:
        self.initialize()
        deleted: dict[str, int] = {}
        artifact_paths: list[str] = []
        with self._lock, self._connect() as db:
            demo_action_rows = db.execute(
                """
                select id, artifact_path, trace_id from approval_actions
                where title = ? or inputs like '%"demo_seed": true%'
                """,
                (DEMO_ACTION_TITLE,),
            ).fetchall()
            demo_action_ids = [row["id"] for row in demo_action_rows]
            artifact_paths = [
                row["artifact_path"] for row in demo_action_rows if row["artifact_path"]
            ]
            demo_trace_ids = [row["trace_id"] for row in demo_action_rows if row["trace_id"]]

            if demo_action_ids:
                placeholders = ",".join("?" for _ in demo_action_ids)
                deleted["artifact_records"] = db.execute(
                    f"delete from artifact_records where action_id in ({placeholders})",
                    demo_action_ids,
                ).rowcount
                deleted["approval_actions"] = db.execute(
                    f"delete from approval_actions where id in ({placeholders})",
                    demo_action_ids,
                ).rowcount

            workflow_rows = db.execute(
                """
                select id, trace_id from workflow_runs_local
                where inputs like '%"demo_seed": true%'
                """
            ).fetchall()
            workflow_trace_ids = [row["trace_id"] for row in workflow_rows if row["trace_id"]]
            deleted["workflow_runs"] = db.execute(
                "delete from workflow_runs_local where inputs like '%\"demo_seed\": true%'"
            ).rowcount

            trace_ids = [*demo_trace_ids, *workflow_trace_ids]
            if trace_ids:
                placeholders = ",".join("?" for _ in trace_ids)
                deleted["linked_traces"] = db.execute(
                    f"delete from trace_runs where id in ({placeholders})",
                    trace_ids,
                ).rowcount
            deleted["demo_traces"] = db.execute(
                """
                delete from trace_runs
                where prompt_version = 'demo-seed-chat-v1'
                   or generated_output like '%"demo_seed": true%'
                """
            ).rowcount

            repo_rows = db.execute(
                "select id from repo_projects where origin_url = ?",
                (DEMO_REPO_FILENAME,),
            ).fetchall()
            repo_ids = [row["id"] for row in repo_rows]
            if repo_ids:
                placeholders = ",".join("?" for _ in repo_ids)
                deleted["code_symbols"] = db.execute(
                    f"delete from code_symbols where project_id in ({placeholders})",
                    repo_ids,
                ).rowcount
                deleted["code_graphs"] = db.execute(
                    f"delete from code_graphs where project_id in ({placeholders})",
                    repo_ids,
                ).rowcount
                deleted["code_risks"] = db.execute(
                    f"delete from code_risk_reports where project_id in ({placeholders})",
                    repo_ids,
                ).rowcount
                deleted["repo_projects"] = db.execute(
                    f"delete from repo_projects where id in ({placeholders})",
                    repo_ids,
                ).rowcount

            source_rows = db.execute(
                "select id from source_documents where uri = ? or uri like 'demo://%'",
                (f"resume://{DEMO_RESUME_FILENAME}",),
            ).fetchall()
            source_ids = [row["id"] for row in source_rows]
            if source_ids:
                placeholders = ",".join("?" for _ in source_ids)
                deleted["resume_profiles"] = db.execute(
                    f"delete from resume_profiles where source_id in ({placeholders})",
                    source_ids,
                ).rowcount
                deleted["memories"] = db.execute(
                    f"delete from memories where source_id in ({placeholders})",
                    source_ids,
                ).rowcount
                deleted["source_documents"] = db.execute(
                    f"delete from source_documents where id in ({placeholders})",
                    source_ids,
                ).rowcount

            journal_rows = db.execute(
                "select id from journal_entries where built like 'Demo seed:%'"
            ).fetchall()
            journal_source_uris = [f"journal://{row['id']}" for row in journal_rows]
            if journal_source_uris:
                placeholders = ",".join("?" for _ in journal_source_uris)
                journal_source_rows = db.execute(
                    f"select id from source_documents where uri in ({placeholders})",
                    journal_source_uris,
                ).fetchall()
                journal_source_ids = [row["id"] for row in journal_source_rows]
                if journal_source_ids:
                    source_placeholders = ",".join("?" for _ in journal_source_ids)
                    deleted["journal_memories"] = db.execute(
                        f"delete from memories where source_id in ({source_placeholders})",
                        journal_source_ids,
                    ).rowcount
                    deleted["journal_sources"] = db.execute(
                        f"delete from source_documents where id in ({source_placeholders})",
                        journal_source_ids,
                    ).rowcount
            deleted["journal_entries"] = db.execute(
                "delete from journal_entries where built like 'Demo seed:%'"
            ).rowcount

            decision_rows = db.execute(
                "select id, memory_id from decision_entries where tags like '%demo_seed%'"
            ).fetchall()
            decision_memory_ids = [row["memory_id"] for row in decision_rows if row["memory_id"]]
            if decision_memory_ids:
                placeholders = ",".join("?" for _ in decision_memory_ids)
                source_rows = db.execute(
                    f"select source_id from memories where id in ({placeholders})",
                    decision_memory_ids,
                ).fetchall()
                source_ids = [row["source_id"] for row in source_rows]
                deleted["decision_memories"] = db.execute(
                    f"delete from memories where id in ({placeholders})",
                    decision_memory_ids,
                ).rowcount
                if source_ids:
                    source_placeholders = ",".join("?" for _ in source_ids)
                    deleted["decision_sources"] = db.execute(
                        f"delete from source_documents where id in ({source_placeholders})",
                        source_ids,
                    ).rowcount
            deleted["decision_entries"] = db.execute(
                "delete from decision_entries where tags like '%demo_seed%'"
            ).rowcount

            profile = db.execute("select * from user_profiles where id = 'default'").fetchone()
            if profile and profile["name"] == "Atlas Demo Builder":
                db.execute(
                    """
                    update user_profiles
                    set name = '', role = 'Student / Developer', current_goals = '[]',
                        target_roles = '[]', skills = '[]', weaknesses = '[]',
                        preferred_tech_stack = '[]', learning_priorities = ?,
                        updated_at = ?
                    where id = 'default'
                    """,
                    (
                        encode_json(["Build Atlas", "Practice interviews", "Ship projects"]),
                        now().isoformat(),
                    ),
                )
                deleted["profile_reset"] = 1

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
