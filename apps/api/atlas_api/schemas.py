from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    title: str
    uri: str | None = None
    snippet: str


class UserProfile(BaseModel):
    id: str = "default"
    name: str = ""
    role: str = ""
    current_goals: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    preferred_tech_stack: list[str] = Field(default_factory=list)
    learning_priorities: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    name: str = ""
    role: str = ""
    current_goals: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    preferred_tech_stack: list[str] = Field(default_factory=list)
    learning_priorities: list[str] = Field(default_factory=list)


class SourceDocument(BaseModel):
    id: str
    title: str
    source_type: str
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MemoryItem(BaseModel):
    id: str
    source_id: str | None = None
    source_title: str
    source_type: str
    memory_type: str = "note"
    title: str | None = None
    content: str | None = None
    summary: str
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    source_references: list[Citation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemoryCreate(BaseModel):
    source_title: str
    source_type: str = "note"
    memory_type: str = "note"
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    importance: float | None = None
    metadata: dict[str, Any] | None = None


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=12)
    memory_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RetrievalHit(BaseModel):
    memory_id: str
    title: str
    memory_type: str
    content: str
    summary: str
    score: float
    tags: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class RetrievalResponse(BaseModel):
    query: str
    hits: list[RetrievalHit] = Field(default_factory=list)


class EmbeddingReindexResponse(BaseModel):
    reindexed_count: int
    provider: str
    model: str
    dimensions: int


class DemoFlowStep(BaseModel):
    id: str
    title: str
    route: str
    status: str
    detail: str
    evidence_count: int = 0


class DemoFlowStatus(BaseModel):
    title: str
    current_mode: str
    completion_percent: int
    next_step: str
    steps: list[DemoFlowStep] = Field(default_factory=list)


class DemoSeedResponse(BaseModel):
    message: str
    created: list[str] = Field(default_factory=list)
    flow: DemoFlowStatus


class DemoResetResponse(BaseModel):
    message: str
    deleted: dict[str, int] = Field(default_factory=dict)
    flow: DemoFlowStatus


class DemoScriptResponse(BaseModel):
    script: str


class ResumeStructuredProfile(BaseModel):
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    id: str
    source_id: str
    filename: str
    raw_text: str
    structured: ResumeStructuredProfile
    created_at: datetime


class ResumeUploadResponse(BaseModel):
    resume: ResumeProfile
    created_memories: list[MemoryItem] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    context: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class ProviderRun(BaseModel):
    provider: str
    model: str
    fallback_used: bool = False
    fallback_reason: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_memories: list[RetrievalHit] = Field(default_factory=list)
    trace_id: str | None = None
    provider: ProviderRun | None = None


class Project(BaseModel):
    id: str
    name: str
    status: str
    summary: str
    repo_path: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)


class TraceStep(BaseModel):
    name: str
    status: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None


class TraceRun(BaseModel):
    id: str
    interaction_type: str
    user_input: str
    retrieved_memories: list[RetrievalHit] = Field(default_factory=list)
    prompt_version: str
    model_used: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    generated_output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int
    errors: list[str] = Field(default_factory=list)
    confidence: float
    assumptions: list[str] = Field(default_factory=list)
    steps: list[TraceStep] = Field(default_factory=list)
    workflow_run_id: str | None = None
    created_at: datetime


class WorkflowDefinition(BaseModel):
    name: str
    description: str
    category: str
    required_inputs: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class WorkflowRunCreate(BaseModel):
    workflow_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunDetail(BaseModel):
    id: str
    workflow_name: str
    status: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[TraceStep] = Field(default_factory=list)
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class JournalEntryCreate(BaseModel):
    built: str
    problems: str = ""
    decisions: str = ""
    skills_used: list[str] = Field(default_factory=list)
    next_tasks: list[str] = Field(default_factory=list)
    entry_date: str | None = None


class JournalEntry(BaseModel):
    id: str
    built: str
    problems: str = ""
    decisions: str = ""
    skills_used: list[str] = Field(default_factory=list)
    next_tasks: list[str] = Field(default_factory=list)
    entry_date: str
    created_at: datetime


class JournalSummary(BaseModel):
    weekly_summary: str
    resume_bullets: list[str] = Field(default_factory=list)
    interview_stories: list[str] = Field(default_factory=list)
    learning_insights: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class RepoConnectRequest(BaseModel):
    github_url: str


class RepoFile(BaseModel):
    path: str
    kind: str
    language: str | None = None
    size_bytes: int = 0
    preview: str | None = None


class RepoProject(BaseModel):
    id: str
    name: str
    origin_type: str
    origin_url: str | None = None
    status: str
    summary: str
    language_stats: dict[str, int] = Field(default_factory=dict)
    readme: str | None = None
    dependency_files: list[str] = Field(default_factory=list)
    file_tree: list[RepoFile] = Field(default_factory=list)
    created_at: datetime


class CodeSymbol(BaseModel):
    id: str
    project_id: str
    name: str
    kind: str
    file_path: str
    language: str | None = None
    line_start: int = 1
    line_end: int = 1
    signature: str | None = None
    evidence: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CodeGraphNode(BaseModel):
    id: str
    label: str
    kind: str
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeGraph(BaseModel):
    project_id: str
    generated_at: datetime
    parser_provider: str
    nodes: list[CodeGraphNode] = Field(default_factory=list)
    edges: list[CodeGraphEdge] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class CodeRiskItem(BaseModel):
    id: str
    project_id: str
    category: str
    severity: str
    title: str
    detail: str
    evidence: str
    file_path: str | None = None
    line: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeRiskReport(BaseModel):
    project_id: str
    generated_at: datetime
    summary: str
    risks: list[CodeRiskItem] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class CodeAnalysisResult(BaseModel):
    project: RepoProject
    symbols: list[CodeSymbol] = Field(default_factory=list)
    graph: CodeGraph
    risk_report: CodeRiskReport


class ApprovalActionCreate(BaseModel):
    tool_name: str
    title: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"


class ApprovalAction(BaseModel):
    id: str
    tool_name: str
    title: str
    status: str
    risk_level: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    preview: str
    result: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str | None = None
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactRecord(BaseModel):
    id: str
    action_id: str
    title: str
    kind: str
    path: str
    content_preview: str
    created_at: datetime


class DashboardSummary(BaseModel):
    metrics: dict[str, int] = Field(default_factory=dict)
    todays_priorities: list[str] = Field(default_factory=list)
    current_projects: list[RepoProject] = Field(default_factory=list)
    pending_workflows: list[WorkflowRunDetail] = Field(default_factory=list)
    pending_approvals: list[ApprovalAction] = Field(default_factory=list)
    recent_memories: list[MemoryItem] = Field(default_factory=list)
    recent_traces: list[TraceRun] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    next_recommended_action: str = ""


class EvaluationPrompt(BaseModel):
    id: str
    category: str
    prompt: str
    success_criteria: list[str] = Field(default_factory=list)


class EvaluationRun(BaseModel):
    id: str
    status: str
    generated_at: datetime
    results: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    trace_id: str | None = None


class PrivacySettingsUpdate(BaseModel):
    allowed_folders: list[str] = Field(default_factory=list)
    blocked_folders: list[str] = Field(default_factory=list)
    redaction_patterns: list[str] = Field(default_factory=list)
    local_only: bool = True
    memory_export_enabled: bool = True


class PrivacySettings(PrivacySettingsUpdate):
    id: str = "default"
    updated_at: datetime


class RedactionPreviewRequest(BaseModel):
    text: str


class RedactionPreviewResponse(BaseModel):
    redacted_text: str
    replacements: list[dict[str, str]] = Field(default_factory=list)


class ForgetMemoryRequest(BaseModel):
    memory_id: str | None = None
    query: str | None = None


class ForgetMemoryResponse(BaseModel):
    deleted_count: int
    deleted_memory_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class MemoryExport(BaseModel):
    exported_at: datetime
    redacted: bool
    memories: list[MemoryItem] = Field(default_factory=list)
    source_count: int = 0


class KnowledgeNode(BaseModel):
    id: str
    label: str
    kind: str
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    evidence: str
    confidence: float = 0.75


class KnowledgeGraph(BaseModel):
    generated_at: datetime
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    metrics: dict[str, int] = Field(default_factory=dict)


class DecisionCreate(BaseModel):
    title: str
    decision: str
    alternatives: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    reason: str
    result: str | None = None
    tags: list[str] = Field(default_factory=list)


class DecisionUpdate(BaseModel):
    result: str | None = None
    tags: list[str] | None = None


class DecisionEntry(BaseModel):
    id: str
    title: str
    decision: str
    alternatives: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    reason: str
    result: str | None = None
    tags: list[str] = Field(default_factory=list)
    memory_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TimelineEvent(BaseModel):
    id: str
    event_type: str
    title: str
    summary: str
    occurred_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillTreeItem(BaseModel):
    id: str
    category: str
    name: str
    level: int
    progress: int
    evidence: list[str] = Field(default_factory=list)
    next_action: str


class SkillTreeResponse(BaseModel):
    generated_at: datetime
    skills: list[SkillTreeItem] = Field(default_factory=list)
    metrics: dict[str, int] = Field(default_factory=dict)


class SelfEvaluationRequest(BaseModel):
    prompt: str = ""
    output: str
    citations: list[Citation] = Field(default_factory=list)
    source_snippets: list[str] = Field(default_factory=list)


class SelfEvaluationResponse(BaseModel):
    grounded: bool
    confidence: float
    hallucination_risk: str
    sources_used: list[str] = Field(default_factory=list)
    verification_items: list[str] = Field(default_factory=list)
    critique: str
    trace_id: str | None = None


class SimulatorScenario(BaseModel):
    id: str
    scenario_type: str
    title: str
    prompt: str
    rubric: list[str] = Field(default_factory=list)


class SimulationStartRequest(BaseModel):
    scenario_id: str


class SimulationAnswerRequest(BaseModel):
    answer: str


class SimulationRun(BaseModel):
    id: str
    scenario: SimulatorScenario
    status: str
    answer: str | None = None
    evaluation: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PluginManifest(BaseModel):
    id: str
    name: str
    category: str
    description: str
    enabled: bool
    permission_scopes: list[str] = Field(default_factory=list)
    status: str = "available"
    config: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class PluginUpdate(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class ModelProvider(BaseModel):
    id: str
    name: str
    mode: str
    endpoint: str | None = None
    status: str
    notes: str


class WorkflowRun(BaseModel):
    id: str
    workflow_name: str
    status: str
    project: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TraceEvent(BaseModel):
    id: str
    span_name: str
    actor: str
    action_type: str
    model: str | None = None
    tool_name: str | None = None
    latency_ms: int | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ApprovalRequest(BaseModel):
    id: str
    action_label: str
    risk_level: str
    status: str
    action_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
