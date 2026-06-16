from datetime import UTC, datetime

from atlas_api.schemas import (
    ApprovalRequest,
    Citation,
    MemoryItem,
    Project,
    TraceEvent,
    WorkflowRun,
)

NOW = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)

SEED_CITATION = Citation(
    source_id="src_resume_atlas",
    title="Resume Project Notes",
    uri="memory://resume/project-notes",
    snippet="Atlas is positioned as a private AI OS with memory, tools, approvals, and traces.",
)

MEMORY_ITEMS = [
    MemoryItem(
        id="mem_atlas_scope",
        source_title="Atlas Product Scope",
        source_type="note",
        summary="Atlas should act as a personal AI OS for projects, career growth, and learning.",
        tags=["product", "career", "learning"],
        confidence=0.94,
        citations=[SEED_CITATION],
    ),
    MemoryItem(
        id="mem_traceability",
        source_title="Safety Principles",
        source_type="spec",
        summary="Every AI action should be traceable and approval-gated when it can change state.",
        tags=["privacy", "safety", "traceability"],
        confidence=0.98,
        citations=[SEED_CITATION],
    ),
]

PROJECTS = [
    Project(
        id="proj_atlas",
        name="Atlas",
        status="active",
        summary="Personal AI OS with memory, workflows, approvals, code intelligence, and traces.",
        repo_path="/Users/harsha/Documents/ATLAS",
        signals={"memory_items": 2, "trace_events": 4, "approval_policy": "strict"},
    )
]

WORKFLOWS = [
    WorkflowRun(
        id="wf_daily_build",
        workflow_name="Daily Build Plan",
        status="ready",
        project="Atlas",
        inputs={"goal": "Implement the first working checkpoint"},
        outputs={"next_step": "Wire real ingestion and workflow execution"},
        created_at=NOW,
    )
]

TRACES = [
    TraceEvent(
        id="trace_command",
        span_name="command.received",
        actor="user",
        action_type="command",
        model=None,
        tool_name=None,
        latency_ms=12,
        citations=[],
        created_at=NOW,
    ),
    TraceEvent(
        id="trace_retrieval",
        span_name="memory.retrieve",
        actor="atlas",
        action_type="retrieval",
        model="embedding-policy-placeholder",
        tool_name="memory.search",
        latency_ms=48,
        citations=[SEED_CITATION],
        created_at=NOW,
    ),
    TraceEvent(
        id="trace_approval",
        span_name="approval.requested",
        actor="atlas",
        action_type="approval",
        model=None,
        tool_name="file.write",
        latency_ms=8,
        citations=[SEED_CITATION],
        created_at=NOW,
    ),
]

APPROVALS = [
    ApprovalRequest(
        id="appr_write_resume",
        action_label="Update resume project bullet draft",
        risk_level="medium",
        status="pending",
        action_payload={"tool": "file.write", "target": "career/resume.md"},
        created_at=NOW,
    )
]
