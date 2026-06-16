# Atlas Product Spec

## Product

Atlas is a personal AI operating system for a student or developer who is building projects, learning new systems, preparing for interviews, and shaping career artifacts. It is designed to be private, traceable, and action-oriented rather than a generic chatbot.

## Target User

The initial target user is a technical builder who has:

- Projects across local codebases, GitHub repositories, notes, resumes, and learning plans.
- A need to connect long-term goals with daily implementation work.
- Interview preparation, resume tailoring, and portfolio storytelling needs.
- A preference for approved automation over opaque autonomous actions.

## Core Promise

Atlas understands the user's personal context and turns it into useful workflows: planning, learning, coding, reviewing, documenting, interview prep, and career artifact generation. Every recommendation should cite the memory, file, trace, or project evidence that informed it.

## MVP Features

- Personal command center with chat-like interaction plus structured workflow outputs.
- Memory vault for notes, resumes, goals, project facts, learning logs, and source citations.
- Source-backed retrieval with citations and confidence metadata.
- Project registry for codebases, career projects, and learning tracks.
- Repository code intelligence with extracted functions, classes, routes, imports, exports,
  file/module/symbol graph data, and deterministic risk analysis.
- Workflow runs for planning, code review, interview prep, resume tailoring, and learning plans.
- Approval queue for tool actions that touch files, repositories, credentials, messages, or external systems.
- Approval-gated action tools for reports, roadmaps, task lists, resume bullets, interview prep docs,
  GitHub issue drafts, and explicit memory writes.
- Local-first privacy mode with allowed folders, blocked folders, memory export, redaction preview,
  local-only policy, and forget controls.
- Personal knowledge graph connecting profile facts, skills, goals, memories, projects, repos,
  decisions, code symbols, concepts, and evidence.
- Decision journal for technical choices, alternatives, tradeoffs, reasons, and later outcomes.
- Growth surfaces: Timeline of You plus a serious skill tree from actual work logs, repo activity,
  and workflow history.
- Self-evaluation mode for grounding, source usage, confidence, hallucination risk, and verification
  items.
- Simulator mode for system design interviews, debugging incidents, production outages, and
  behavioral answers.
- Plugin architecture and hybrid model provider surface for cloud LLMs and local Ollama/vLLM-style
  endpoints.
- Trace timeline for every AI plan, retrieval call, tool call, approval decision, and final action.
- Local evaluation suite for resume bullet quality, retrieval accuracy, codebase Q&A, workflow
  reliability, citation quality, and hallucination checks.
- Backend health, configuration, database connection, typed API routing, and error handling.
- Polished dashboard UI with pages for command, profile, resume, memory, workflows, journal,
  projects, code intelligence, actions, traces, evaluations, and settings.
- Docker Compose for local development with API, web, PostgreSQL, pgvector, and Redis.

## Full-Version Features

- Multi-provider LLM orchestration with per-workflow model policies.
- LangGraph or OpenAI Agents SDK workflows with resumable state.
- Deeper tree-sitter grammars for more languages and richer call graph resolution.
- Personal knowledge ingestion for Markdown, PDF, DOCX, code, GitHub issues, resumes, and transcripts.
- Memory lifecycle controls: pinning, decay, archival, conflict detection, and source revalidation.
- Career artifact studio for resumes, cover letters, project writeups, LinkedIn summaries, and interview stories.
- Learning coach with skill maps, spaced review, practice prompts, and progress evidence.
- Secure action tools for local files, Git, calendars, email drafts, GitHub, and task systems.
- Observability dashboard with traces, cost, latency, retrieval quality, workflow success, and approval analytics.
- Deployment profiles for local-only, private VPS, and managed cloud.

## Non-Goals

- Atlas is not a general consumer voice assistant.
- Atlas is not designed to take irreversible actions without explicit approval.
- Atlas is not a replacement for a secure password manager or secrets vault.
- Atlas is not a surveillance product and should not ingest private data silently.
- Atlas is not initially optimized for teams, organizations, or multi-tenant enterprise use.

## Safety And Privacy Principles

- Private by default: local-first development and explicit connectors.
- Source-backed memory: every durable memory points to evidence or a user-authored assertion.
- Approval gates: file writes, external messages, repository changes, and credential use require approval.
- Traceability: every AI action creates a trace event with inputs, outputs, model/tool metadata, and citations.
- Revocability: the user can delete memories, sources, workflow traces, and connector grants.
- Least privilege: tools get scoped capabilities, not broad ambient authority.
- Human-readable state: memory, approvals, workflows, and traces are inspectable in the UI.
- No hidden autonomy: scheduled or background work is visible, pausable, and auditable.
