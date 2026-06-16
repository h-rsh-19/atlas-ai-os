# Atlas MVP Scope

## MVP Goal

Ship a credible personal AI OS checkpoint that demonstrates the product loop:

1. Add or inspect personal context.
2. Ask Atlas to perform a structured task.
3. Retrieve source-backed memory.
4. Produce a workflow plan with citations.
5. Request approval before any sensitive action.
6. Record trace events for the full interaction.

Current mode: local deterministic prototype with LLM-ready architecture. The checkpoint includes
provider interfaces and configuration for OpenAI-compatible, Ollama, and vLLM-style generation and
embeddings, but defaults to deterministic local fallbacks for repeatable tests and offline demos.

## Included In This Checkpoint

- Monorepo with `apps/web`, `apps/api`, `docs`, `docker`, and `scripts`.
- FastAPI service with health endpoints, configuration, logging, typed routes, and database models.
- PostgreSQL plus pgvector and Redis in Docker Compose.
- Internal data model for users, memory sources, memory items, projects, workflow runs, trace events, and approval requests.
- Next.js dashboard with navigation, command center, memory, workflows, projects, traces, and settings.
- React Flow workflow graph page.
- Personal profile storage and editing for goals, roles, skills, weaknesses, stack, and priorities.
- Resume PDF upload with raw extracted text plus structured education, experience, projects, skills, certifications, and achievements.
- Memory CRUD with source documents, tags, timestamps, importance, metadata, source references, and embeddings.
- Retrieval endpoint that chunks/embeds memory, searches relevant context, and returns citations.
- Context-aware chat that uses retrieved personal context and avoids generic answers.
- Trace logging for chat/workflow interactions with input, memory evidence, prompt version, model, tools, output, latency, errors, confidence, assumptions, and step detail.
- Workflow engine MVP for day/week planning, project journaling, resume bullets, interview answers, learning plans, and career intelligence.
- Project journal entries with weekly summaries, resume bullets, interview stories, and learning insights.
- Repo ingestion from GitHub URL metadata or local ZIP upload with file tree, language stats, README, dependency files, source previews, and project memory.
- Static code intelligence over uploaded repositories:
  functions, classes, routes, imports, exports, modules, dependency files, graph nodes, graph edges,
  and searchable symbols.
- Dependency and symbol graph visualization with React Flow.
- Deterministic code risk reports for large files, complex files, circular imports, missing tests,
  dependency hotspots, duplicated-looking modules, weak README/docs, and TODO/FIXME hotspots.
- Codebase workflows for architecture summaries, onboarding guides, refactor plans, test plans,
  PR review drafts, and bug investigation plans with file citations.
- Approval-gated action tools for real Markdown artifacts and explicit memory writes.
- Personal command center with live priorities, current projects, pending approvals, recent memory,
  recent traces, weak areas, and next recommended action.
- Optional browser voice interface with speech-to-text command input and text-to-speech response.
- Local evaluation suite and API tests for retrieval, workflows, citations, codebase Q&A, and safety.
- Local-first privacy controls for allowed folders, blocked folders, redaction, memory export, and
  forget actions.
- Personal knowledge graph over skills, projects, goals, tasks, notes, repos, people, concepts, and
  decisions.
- Decision journal with alternatives, tradeoffs, reasons, and result-later updates.
- Timeline of You and skill tree/growth map from actual Atlas activity.
- Per-output self-evaluation and hallucination checker.
- Simulator mode with rubric-based answer evaluation.
- Plugin registry and hybrid cloud/local model provider surface.
- Golden demo page backed by `/api/demo/flow` for the resume -> profile/goals -> memory retrieval ->
  repo upload -> code analysis -> workflow -> approval -> artifact -> trace story.
- README with quickstart, architecture summary, and demo flow.
- Initial test setup for API and frontend lint/build verification.

## Deferred

- Production provider hardening: retries, budgets, streaming, model-specific policies, and key
  management.
- Durable ingestion pipelines beyond profile, manual memory, and resume upload.
- Full grammar-backed tree-sitter indexing for every supported language. The current checkpoint
  uses Python AST plus TypeScript/JavaScript heuristics and detects optional tree-sitter packages.
- LangGraph/OpenAI Agents SDK runtime.
- Authentication and user account management.
- Production deployment hardening.
- External connectors.
- Remote GitHub API cloning/fetching without ZIP upload.
- OCR for scanned resume PDFs.

## MVP Workflows

- Daily Build Plan: turns project state and goals into an implementation plan.
- Code Review Prep: maps codebase evidence into risks and suggested tests.
- Interview Drill: builds practice prompts from resume/project memory.
- Resume Tailor: drafts role-specific bullets with citations to project evidence.
- Learning Sprint: creates a focused learning loop with checkpoints and review prompts.

## Acceptance Criteria

- The API starts locally and returns healthy status from `/healthz`.
- Docker Compose defines web, API, PostgreSQL with pgvector, and Redis services.
- The UI starts locally and provides the main workspace pages.
- The user can create/edit a personal profile.
- The user can upload a PDF resume and inspect parsed structured sections.
- The user can create, read, update, delete, and retrieve memories with citations.
- Chat answers are grounded in stored memory and show citations.
- Trace page shows every chat/workflow run and supports detail inspection.
- User can run named workflows and see progress steps.
- User can save project journal entries and generate career/learning artifacts.
- User can ingest a repository ZIP and inspect the project file tree and summary.
- User can run code analysis, search symbols, inspect graph relationships, and review risk evidence.
- User can propose, preview, approve, reject, and audit tool actions before any write occurs.
- User can run local evals and inspect pass/needs-data results with trace linkage.
- User can inspect and edit local privacy scopes, preview redaction, export memory, and forget memory.
- User can inspect a personal knowledge graph and timeline/skill tree derived from real stored data.
- User can capture technical decisions and update their results later.
- User can run simulator scenarios and receive rubric-based feedback.
- User can toggle plugin capabilities and inspect cloud/local model provider options.
- User can open Demo and see live completion state for the golden end-to-end story.
- The architecture docs explain how memory, retrieval, workflows, tools, approvals, and traces fit together.
- Tests or validation commands are documented and runnable.
