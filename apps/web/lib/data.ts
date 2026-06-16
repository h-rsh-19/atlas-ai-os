import {
  BadgeCheck,
  BookOpenCheck,
  Brain,
  BriefcaseBusiness,
  ClipboardCheck,
  Code2,
  FileUp,
  Gamepad2,
  GitBranch,
  LibraryBig,
  LockKeyhole,
  Map,
  Network,
  NotebookTabs,
  Puzzle,
  Radar,
  Route,
  Settings2,
  ShieldCheck,
  TestTubeDiagonal,
  Sparkles,
  SquareActivity,
  UserRound,
  Workflow
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Command", icon: Sparkles },
  { href: "/demo", label: "Demo", icon: Route },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/resume", label: "Resume", icon: FileUp },
  { href: "/memory", label: "Memory", icon: Brain },
  { href: "/privacy", label: "Privacy", icon: LockKeyhole },
  { href: "/knowledge", label: "Graph", icon: Network },
  { href: "/growth", label: "Growth", icon: Map },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/journal", label: "Journal", icon: LibraryBig },
  { href: "/decisions", label: "Decisions", icon: GitBranch },
  { href: "/projects", label: "Projects", icon: Code2 },
  { href: "/code", label: "Code Intel", icon: Network },
  { href: "/actions", label: "Actions", icon: ClipboardCheck },
  { href: "/simulator", label: "Simulator", icon: Gamepad2 },
  { href: "/traces", label: "Traces", icon: SquareActivity },
  { href: "/evals", label: "Evals", icon: TestTubeDiagonal },
  { href: "/plugins", label: "Plugins", icon: Puzzle },
  { href: "/providers", label: "Providers", icon: Radar },
  { href: "/settings", label: "Settings", icon: Settings2 }
];

export const metricCards = [
  { label: "Cited Memories", value: "128", delta: "+14 this week", icon: NotebookTabs },
  { label: "Workflow Runs", value: "36", delta: "92% completed", icon: Route },
  { label: "Approval Gates", value: "9", delta: "3 pending", icon: ShieldCheck },
  { label: "Indexed Symbols", value: "4.8k", delta: "Atlas repo active", icon: Network }
];

export const contextStack = [
  {
    title: "Resume Project Notes",
    type: "Career",
    confidence: "94%",
    snippet: "Atlas is framed as a private AI OS with memory, approvals, and traces."
  },
  {
    title: "Learning Roadmap",
    type: "Learning",
    confidence: "89%",
    snippet: "Priority areas: backend architecture, AI systems, code intelligence, deployment."
  },
  {
    title: "ATLAS Workspace",
    type: "Codebase",
    confidence: "97%",
    snippet: "Monorepo checkpoint with FastAPI, Next.js, PostgreSQL, Redis, and Docker."
  }
];

export const activeWorkflows = [
  {
    name: "Daily Build Plan",
    status: "Ready",
    owner: "Atlas",
    next: "Wire ingestion and workflow execution",
    evidence: "3 citations"
  },
  {
    name: "Interview Drill",
    status: "Drafting",
    owner: "Career Coach",
    next: "Generate project-based system design prompts",
    evidence: "5 citations"
  },
  {
    name: "Code Review Prep",
    status: "Waiting",
    owner: "Reviewer",
    next: "Index tree-sitter symbols",
    evidence: "1 repo"
  }
];

export const approvalQueue = [
  {
    action: "Update resume project bullet draft",
    risk: "Medium",
    tool: "file.write",
    target: "career/resume.md"
  },
  {
    action: "Create study sprint tasks",
    risk: "Low",
    tool: "tasks.create",
    target: "Learning Sprint"
  },
  {
    action: "Run dependency graph scan",
    risk: "Low",
    tool: "code.index",
    target: "ATLAS"
  }
];

export const traceEvents = [
  {
    span: "command.received",
    actor: "User",
    kind: "Command",
    latency: "12 ms",
    detail: "Build the first Atlas checkpoint"
  },
  {
    span: "memory.retrieve",
    actor: "Atlas",
    kind: "Retrieval",
    latency: "48 ms",
    detail: "3 cited memories selected"
  },
  {
    span: "workflow.plan",
    actor: "Atlas",
    kind: "Reasoning",
    latency: "640 ms",
    detail: "5-step implementation plan created"
  },
  {
    span: "approval.requested",
    actor: "Atlas",
    kind: "Approval",
    latency: "8 ms",
    detail: "file.write requires explicit approval"
  }
];

export const memoryRows = [
  {
    title: "Atlas Product Scope",
    source: "docs/product-spec.md",
    type: "Spec",
    confidence: "98%",
    tags: ["product", "privacy", "career"],
    evidence: "Personal AI OS for engineering, learning, and career growth."
  },
  {
    title: "MVP Workflow Loop",
    source: "docs/mvp-scope.md",
    type: "Plan",
    confidence: "96%",
    tags: ["workflow", "retrieval", "approvals"],
    evidence: "Retrieve source-backed memory, produce a cited plan, request approval."
  },
  {
    title: "Traceability Rule",
    source: "docs/architecture.md",
    type: "Architecture",
    confidence: "99%",
    tags: ["traces", "observability"],
    evidence: "AI actions record actor, span, metadata, citations, latency, and payloads."
  }
];

export const projectRows = [
  {
    name: "Atlas",
    status: "Active",
    language: "TypeScript + Python",
    summary: "Personal AI OS with memory, workflows, approvals, code intelligence, and traces.",
    signals: [
      { label: "API Routes", value: "7" },
      { label: "Trace Tables", value: "1" },
      { label: "Memory Models", value: "2" }
    ]
  },
  {
    name: "Career System",
    status: "Planned",
    language: "Markdown + AI Workflows",
    summary: "Resume tailoring, interview story generation, and recruiter-ready artifacts.",
    signals: [
      { label: "Artifacts", value: "4" },
      { label: "Citations", value: "12" },
      { label: "Review Gates", value: "2" }
    ]
  }
];

export const settingsSections = [
  {
    title: "Model Policy",
    icon: BadgeCheck,
    rows: ["Provider: OpenAI-compatible", "Embeddings: 1536 dimensions", "Sensitive actions: approval required"]
  },
  {
    title: "Privacy",
    icon: LockKeyhole,
    rows: ["Memory: source-backed", "Retention: user controlled", "Connectors: explicit only"]
  },
  {
    title: "Learning",
    icon: BookOpenCheck,
    rows: ["Sprint cadence: weekly", "Review mode: spaced prompts", "Evidence: project-linked"]
  },
  {
    title: "Code Intelligence",
    icon: GitBranch,
    rows: [
      "Parser: AST plus TS/JS heuristics",
      "Graph: stored file, symbol, import, and call edges",
      "Scope: approved repos"
    ]
  },
  {
    title: "Career",
    icon: BriefcaseBusiness,
    rows: ["Artifacts: resume and interview stories", "Tone: recruiter-ready", "Claims: citation required"]
  },
  {
    title: "Monitoring",
    icon: Radar,
    rows: ["Traces: internal table", "Costs: planned", "Latency: captured per event"]
  }
];
