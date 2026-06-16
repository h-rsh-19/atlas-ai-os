export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type Citation = {
  source_id: string;
  title: string;
  uri?: string | null;
  snippet: string;
};

export type UserProfile = {
  id: string;
  name: string;
  role: string;
  current_goals: string[];
  target_roles: string[];
  skills: string[];
  weaknesses: string[];
  preferred_tech_stack: string[];
  learning_priorities: string[];
  updated_at?: string | null;
};

export type MemoryItem = {
  id: string;
  source_id?: string | null;
  source_title: string;
  source_type: string;
  memory_type: string;
  title?: string | null;
  content?: string | null;
  summary: string;
  tags: string[];
  importance: number;
  citations: Citation[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type RetrievalHit = {
  memory_id: string;
  title: string;
  memory_type: string;
  content: string;
  summary: string;
  score: number;
  tags: string[];
  citations: Citation[];
};

export type EmbeddingReindexResponse = {
  reindexed_count: number;
  provider: string;
  model: string;
  dimensions: number;
};

export type DemoFlowStep = {
  id: string;
  title: string;
  route: string;
  status: "completed" | "ready" | "pending";
  detail: string;
  evidence_count: number;
};

export type DemoFlowStatus = {
  title: string;
  current_mode: string;
  completion_percent: number;
  next_step: string;
  steps: DemoFlowStep[];
};

export type TraceStep = {
  name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  tool_calls: Record<string, unknown>[];
  latency_ms: number;
  error?: string | null;
};

export type TraceRun = {
  id: string;
  interaction_type: string;
  user_input: string;
  retrieved_memories: RetrievalHit[];
  prompt_version: string;
  model_used: string;
  tool_calls: Record<string, unknown>[];
  generated_output: Record<string, unknown>;
  latency_ms: number;
  errors: string[];
  confidence: number;
  assumptions: string[];
  steps: TraceStep[];
  workflow_run_id?: string | null;
  created_at: string;
};

export type WorkflowDefinition = {
  name: string;
  description: string;
  category: string;
  required_inputs: string[];
  steps: string[];
};

export type WorkflowRun = {
  id: string;
  workflow_name: string;
  status: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  steps: TraceStep[];
  trace_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type JournalEntry = {
  id: string;
  built: string;
  problems: string;
  decisions: string;
  skills_used: string[];
  next_tasks: string[];
  entry_date: string;
  created_at: string;
};

export type JournalSummary = {
  weekly_summary: string;
  resume_bullets: string[];
  interview_stories: string[];
  learning_insights: string[];
  citations: Citation[];
};

export type RepoFile = {
  path: string;
  kind: string;
  language?: string | null;
  size_bytes: number;
  preview?: string | null;
};

export type RepoProject = {
  id: string;
  name: string;
  origin_type: string;
  origin_url?: string | null;
  status: string;
  summary: string;
  language_stats: Record<string, number>;
  readme?: string | null;
  dependency_files: string[];
  file_tree: RepoFile[];
  created_at: string;
};

export type CodeSymbol = {
  id: string;
  project_id: string;
  name: string;
  kind: string;
  file_path: string;
  language?: string | null;
  line_start: number;
  line_end: number;
  signature?: string | null;
  evidence: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type CodeGraphNode = {
  id: string;
  label: string;
  kind: string;
  file_path?: string | null;
  metadata: Record<string, unknown>;
};

export type CodeGraphEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
  evidence?: string | null;
  metadata: Record<string, unknown>;
};

export type CodeGraph = {
  project_id: string;
  generated_at: string;
  parser_provider: string;
  nodes: CodeGraphNode[];
  edges: CodeGraphEdge[];
  metrics: Record<string, unknown>;
};

export type CodeRiskItem = {
  id: string;
  project_id: string;
  category: string;
  severity: string;
  title: string;
  detail: string;
  evidence: string;
  file_path?: string | null;
  line?: number | null;
  metadata: Record<string, unknown>;
};

export type CodeRiskReport = {
  project_id: string;
  generated_at: string;
  summary: string;
  risks: CodeRiskItem[];
  metrics: Record<string, unknown>;
};

export type CodeAnalysisResult = {
  project: RepoProject;
  symbols: CodeSymbol[];
  graph: CodeGraph;
  risk_report: CodeRiskReport;
};

export type ApprovalAction = {
  id: string;
  tool_name: string;
  title: string;
  status: string;
  risk_level: string;
  inputs: Record<string, unknown>;
  preview: string;
  result: Record<string, unknown>;
  artifact_path?: string | null;
  trace_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ArtifactRecord = {
  id: string;
  action_id: string;
  title: string;
  kind: string;
  path: string;
  content_preview: string;
  created_at: string;
};

export type DashboardSummary = {
  metrics: Record<string, number>;
  todays_priorities: string[];
  current_projects: RepoProject[];
  pending_workflows: WorkflowRun[];
  pending_approvals: ApprovalAction[];
  recent_memories: MemoryItem[];
  recent_traces: TraceRun[];
  weak_areas: string[];
  next_recommended_action: string;
};

export type EvaluationPrompt = {
  id: string;
  category: string;
  prompt: string;
  success_criteria: string[];
};

export type EvaluationRun = {
  id: string;
  status: string;
  generated_at: string;
  results: Array<Record<string, unknown>>;
  summary: string;
  trace_id?: string | null;
};

export type PrivacySettings = {
  id: string;
  allowed_folders: string[];
  blocked_folders: string[];
  redaction_patterns: string[];
  local_only: boolean;
  memory_export_enabled: boolean;
  updated_at: string;
};

export type MemoryExport = {
  exported_at: string;
  redacted: boolean;
  memories: MemoryItem[];
  source_count: number;
};

export type KnowledgeNode = {
  id: string;
  label: string;
  kind: string;
  weight: number;
  metadata: Record<string, unknown>;
};

export type KnowledgeEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
  evidence: string;
  confidence: number;
};

export type KnowledgeGraph = {
  generated_at: string;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  metrics: Record<string, number>;
};

export type DecisionEntry = {
  id: string;
  title: string;
  decision: string;
  alternatives: string[];
  tradeoffs: string[];
  reason: string;
  result?: string | null;
  tags: string[];
  memory_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  title: string;
  summary: string;
  occurred_at: string;
  metadata: Record<string, unknown>;
};

export type SkillTreeItem = {
  id: string;
  category: string;
  name: string;
  level: number;
  progress: number;
  evidence: string[];
  next_action: string;
};

export type SkillTreeResponse = {
  generated_at: string;
  skills: SkillTreeItem[];
  metrics: Record<string, number>;
};

export type SelfEvaluationResponse = {
  grounded: boolean;
  confidence: number;
  hallucination_risk: string;
  sources_used: string[];
  verification_items: string[];
  critique: string;
  trace_id?: string | null;
};

export type SimulatorScenario = {
  id: string;
  scenario_type: string;
  title: string;
  prompt: string;
  rubric: string[];
};

export type SimulationRun = {
  id: string;
  scenario: SimulatorScenario;
  status: string;
  answer?: string | null;
  evaluation: Record<string, unknown>;
  trace_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type PluginManifest = {
  id: string;
  name: string;
  category: string;
  description: string;
  enabled: boolean;
  permission_scopes: string[];
  status: string;
  config: Record<string, unknown>;
  updated_at: string;
};

export type ModelProvider = {
  id: string;
  name: string;
  mode: string;
  endpoint?: string | null;
  status: string;
  notes: string;
};

export type ResumeProfile = {
  id: string;
  source_id: string;
  filename: string;
  raw_text: string;
  structured: {
    education: string[];
    experience: string[];
    projects: string[];
    skills: string[];
    certifications: string[];
    achievements: string[];
  };
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {})
    }
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getProfile() {
  return request<UserProfile>("/api/profile");
}

export function updateProfile(payload: Omit<UserProfile, "id" | "updated_at">) {
  return request<UserProfile>("/api/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function listMemories() {
  return request<MemoryItem[]>("/api/memory");
}

export function createMemory(payload: {
  source_title: string;
  source_type: string;
  memory_type: string;
  title?: string;
  content: string;
  tags: string[];
  importance: number;
}) {
  return request<MemoryItem>("/api/memory", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteMemory(memoryId: string) {
  return request<void>(`/api/memory/${memoryId}`, { method: "DELETE" });
}

export function searchMemory(query: string) {
  return request<{ query: string; hits: RetrievalHit[] }>("/api/retrieval/query", {
    method: "POST",
    body: JSON.stringify({ query, top_k: 6 })
  });
}

export function reindexEmbeddings() {
  return request<EmbeddingReindexResponse>("/api/memory/embeddings/reindex", {
    method: "POST"
  });
}

export function getDemoFlow() {
  return request<DemoFlowStatus>("/api/demo/flow");
}

export async function uploadResume(file: File) {
  const response = await fetch(
    `${API_BASE_URL}/api/resume/upload?filename=${encodeURIComponent(file.name)}`,
    {
      method: "POST",
      headers: { "content-type": "application/pdf" },
      body: await file.arrayBuffer()
    }
  );
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Upload failed with ${response.status}`);
  }
  return (await response.json()) as { resume: ResumeProfile; created_memories: MemoryItem[] };
}

export function getLatestResume() {
  return request<ResumeProfile | null>("/api/resume/latest");
}

export function sendChat(message: string, context?: string) {
  return request<{
    answer: string;
    citations: Citation[];
    retrieved_memories: RetrievalHit[];
    trace_id?: string | null;
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, context, top_k: 5 })
  });
}

export function listTraces() {
  return request<TraceRun[]>("/api/traces");
}

export function getTrace(traceId: string) {
  return request<TraceRun>(`/api/traces/${traceId}`);
}

export function listWorkflowDefinitions() {
  return request<WorkflowDefinition[]>("/api/workflows/definitions");
}

export function listWorkflowRuns() {
  return request<WorkflowRun[]>("/api/workflows");
}

export function runWorkflow(workflow_name: string, inputs: Record<string, unknown>) {
  return request<WorkflowRun>("/api/workflows/run", {
    method: "POST",
    body: JSON.stringify({ workflow_name, inputs })
  });
}

export function listJournalEntries() {
  return request<JournalEntry[]>("/api/journal");
}

export function createJournalEntry(payload: {
  built: string;
  problems: string;
  decisions: string;
  skills_used: string[];
  next_tasks: string[];
}) {
  return request<JournalEntry>("/api/journal", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getJournalSummary() {
  return request<JournalSummary>("/api/journal/summary");
}

export function listProjects() {
  return request<RepoProject[]>("/api/projects");
}

export function connectGithubRepo(github_url: string) {
  return request<RepoProject>("/api/projects/github", {
    method: "POST",
    body: JSON.stringify({ github_url })
  });
}

export async function uploadRepoZip(file: File) {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/zip?filename=${encodeURIComponent(file.name)}`,
    {
      method: "POST",
      headers: { "content-type": "application/zip" },
      body: await file.arrayBuffer()
    }
  );
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Upload failed with ${response.status}`);
  }
  return (await response.json()) as RepoProject;
}

export function getDashboard() {
  return request<DashboardSummary>("/api/dashboard");
}

export function analyzeCodebase(projectId: string) {
  return request<CodeAnalysisResult>(`/api/code/analyze/${projectId}`, {
    method: "POST"
  });
}

export function listCodeSymbols(projectId?: string, query?: string) {
  const params = new URLSearchParams();
  if (projectId) {
    params.set("project_id", projectId);
  }
  if (query) {
    params.set("query", query);
  }
  params.set("limit", "200");
  return request<CodeSymbol[]>(`/api/code/symbols?${params.toString()}`);
}

export function getCodeGraph(projectId: string) {
  return request<CodeGraph>(`/api/code/graph/${projectId}`);
}

export function getCodeRisks(projectId: string) {
  return request<CodeRiskReport>(`/api/code/risks/${projectId}`);
}

export function listActions() {
  return request<ApprovalAction[]>("/api/actions");
}

export function proposeAction(payload: {
  tool_name: string;
  title: string;
  risk_level: string;
  inputs: Record<string, unknown>;
}) {
  return request<ApprovalAction>("/api/actions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function approveAction(actionId: string) {
  return request<ApprovalAction>(`/api/actions/${actionId}/approve`, { method: "POST" });
}

export function rejectAction(actionId: string) {
  return request<ApprovalAction>(`/api/actions/${actionId}/reject`, { method: "POST" });
}

export function listArtifacts() {
  return request<ArtifactRecord[]>("/api/actions/artifacts");
}

export function listEvaluationPrompts() {
  return request<EvaluationPrompt[]>("/api/evals/prompts");
}

export function listEvaluationRuns() {
  return request<EvaluationRun[]>("/api/evals");
}

export function runEvaluations() {
  return request<EvaluationRun>("/api/evals/run", { method: "POST" });
}

export function getPrivacySettings() {
  return request<PrivacySettings>("/api/privacy");
}

export function updatePrivacySettings(payload: Omit<PrivacySettings, "id" | "updated_at">) {
  return request<PrivacySettings>("/api/privacy", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function redactPreview(text: string) {
  return request<{ redacted_text: string; replacements: Record<string, string>[] }>(
    "/api/privacy/redact",
    {
      method: "POST",
      body: JSON.stringify({ text })
    }
  );
}

export function exportMemory(redacted = true) {
  return request<MemoryExport>(`/api/privacy/export?redacted=${redacted}`);
}

export function forgetMemory(payload: { memory_id?: string; query?: string }) {
  return request<{ deleted_count: number; deleted_memory_ids: string[]; trace_id?: string | null }>(
    "/api/privacy/forget",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function getKnowledgeGraph() {
  return request<KnowledgeGraph>("/api/knowledge/graph");
}

export function listDecisions() {
  return request<DecisionEntry[]>("/api/decisions");
}

export function createDecision(payload: {
  title: string;
  decision: string;
  alternatives: string[];
  tradeoffs: string[];
  reason: string;
  result?: string;
  tags: string[];
}) {
  return request<DecisionEntry>("/api/decisions", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateDecision(decisionId: string, payload: { result?: string; tags?: string[] }) {
  return request<DecisionEntry>(`/api/decisions/${decisionId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getTimeline() {
  return request<TimelineEvent[]>("/api/growth/timeline");
}

export function getSkillTree() {
  return request<SkillTreeResponse>("/api/growth/skills");
}

export function selfEvaluate(payload: {
  prompt: string;
  output: string;
  citations: Citation[];
  source_snippets: string[];
}) {
  return request<SelfEvaluationResponse>("/api/self-eval", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listSimulatorScenarios() {
  return request<SimulatorScenario[]>("/api/simulator/scenarios");
}

export function listSimulationRuns() {
  return request<SimulationRun[]>("/api/simulator");
}

export function startSimulation(scenario_id: string) {
  return request<SimulationRun>("/api/simulator/start", {
    method: "POST",
    body: JSON.stringify({ scenario_id })
  });
}

export function answerSimulation(runId: string, answer: string) {
  return request<SimulationRun>(`/api/simulator/${runId}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer })
  });
}

export function listPlugins() {
  return request<PluginManifest[]>("/api/plugins");
}

export function updatePlugin(pluginId: string, payload: { enabled?: boolean; config?: Record<string, unknown> }) {
  return request<PluginManifest>(`/api/plugins/${pluginId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function listModelProviders() {
  return request<ModelProvider[]>("/api/plugins/models/providers");
}
