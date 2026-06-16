from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlas_api.db.base import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    memory_sources: Mapped[list["MemorySource"]] = relationship(back_populates="user")
    projects: Mapped[list["Project"]] = relationship(back_populates="user")


class MemorySource(Base):
    __tablename__ = "memory_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    uri: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(128), index=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship(back_populates="memory_sources")
    items: Mapped[list["MemoryItem"]] = relationship(back_populates="source")


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("memory_sources.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    source: Mapped["MemorySource"] = relationship(back_populates="items")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    repo_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="active", index=True)
    project_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped["User"] = relationship(back_populates="projects")
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="project")
    code_nodes: Mapped[list["CodeNode"]] = relationship(back_populates="project")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    workflow_name: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(60), default="queued", index=True)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    project: Mapped["Project | None"] = relationship(back_populates="workflow_runs")
    trace_events: Mapped[list["TraceEvent"]] = relationship(back_populates="workflow_run")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="workflow_run")


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    span_name: Mapped[str] = mapped_column(String(200), index=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    action_type: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str | None] = mapped_column(String(120))
    tool_name: Mapped[str | None] = mapped_column(String(160), index=True)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    citations: Mapped[list[dict]] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workflow_run: Mapped["WorkflowRun | None"] = relationship(back_populates="trace_events")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    action_label: Mapped[str] = mapped_column(String(240))
    action_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(60), default="pending", index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="atlas")
    decided_by: Mapped[str | None] = mapped_column(String(120))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_run: Mapped["WorkflowRun | None"] = relationship(back_populates="approval_requests")


class CodeNode(Base):
    __tablename__ = "code_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    node_type: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    node_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="code_nodes")
    outgoing_edges: Mapped[list["CodeEdge"]] = relationship(
        back_populates="from_node", foreign_keys="CodeEdge.from_node_id"
    )


class CodeEdge(Base):
    __tablename__ = "code_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    from_node_id: Mapped[str] = mapped_column(ForeignKey("code_nodes.id"), index=True)
    to_node_id: Mapped[str] = mapped_column(ForeignKey("code_nodes.id"), index=True)
    edge_type: Mapped[str] = mapped_column(String(80), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    edge_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    from_node: Mapped["CodeNode"] = relationship(foreign_keys=[from_node_id])
    to_node: Mapped["CodeNode"] = relationship(foreign_keys=[to_node_id])
