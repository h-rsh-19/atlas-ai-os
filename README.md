# Atlas

Atlas is a private, traceable personal AI operating system for engineering work, learning, career
planning, and daily productivity. It is built as a serious early-stage AI product: memory has source
evidence, workflows are named and observable, repository code intelligence is inspectable, and write
actions require approval.

## Problem

Students and developers usually scatter their context across resumes, notes, repos, project logs,
learning plans, and interview prep documents. Generic chatbots do not know that context, cannot cite
where claims came from, and often blur the line between suggestion and action.

## Solution

Atlas centralizes personal context and turns it into grounded workflows:

- Learn what to study next from profile, resume, memory, and journal evidence.
- Convert project logs into resume bullets and interview stories.
- Ingest repositories, extract symbols, build dependency graphs, and surface code risks.
- Run named workflows for planning, career intelligence, and codebase understanding.
- Propose artifacts and memory writes behind explicit approval gates.
- Inspect traces for every chat, workflow, evaluation, and approved action.

## Features

- Personal profile system for goals, roles, skills, weak areas, stack, and learning priorities.
- Resume PDF upload with raw text storage and structured section extraction.
- Source-backed memory CRUD with metadata, importance, tags, citations, and deterministic embeddings.
- Retrieval and context-aware chat with cited sources and trace IDs.
- Workflow engine for daily planning, weekly planning, journals, resume bullets, interview answers,
  learning plans, career analysis, and codebase workflows.
- Project journal system that generates weekly summaries, resume bullets, interview stories, and
  learning insights.
- Repository ingestion from GitHub URL metadata or local ZIP upload.
- Static code intelligence for functions, classes, routes, imports, exports, modules, and dependency
  files using Python AST plus TypeScript/JavaScript heuristics.
- React Flow graph visualization for file, symbol, import, contains, and call relationships.
- Deterministic code risk reports with evidence for large files, complex files, circular dependencies,
  missing tests, dependency hotspots, duplicated-looking modules, weak README/docs, and TODO/FIXME
  hotspots.
- Approval-gated action tools for Markdown reports, roadmaps, task lists, resume bullets, interview
  prep docs, GitHub issue drafts, and explicit memory writes.
- Local-first privacy controls for allowed folders, blocked folders, memory export, redaction preview,
  and user-initiated forget actions.
- Personal knowledge graph connecting skills, projects, goals, notes, repos, decisions, concepts, and
  code symbols.
- Decision journal for technical decisions, alternatives, tradeoffs, reasons, tags, and later results.
- Timeline of You plus a serious skill tree/RPG-style growth map from actual work logs, repos, and
  workflow evidence.
- Simulator mode for system design, debugging incidents, production outages, and behavioral interview
  drills with rubric-based evaluation.
- Plugin registry for GitHub, calendar, file, resume, repo analyzer, and interview coach capabilities.
- Hybrid model provider surface for cloud LLMs plus local Ollama/vLLM-style endpoints.
- Personal command center with priorities, projects, pending approvals, recent memory, recent traces,
  weak areas, and next recommended action.
- Optional browser voice command mode with speech-to-text input and text-to-speech response.
- Local evaluation suite for resume bullet quality, retrieval accuracy, codebase Q&A correctness,
  workflow reliability, citation quality, and hallucination checks.

## Architecture

```text
apps/
  api/       FastAPI backend, local store, workflows, code intelligence, traces
  web/       Next.js dashboard, React Flow graph UI, approval/action surfaces
docs/        Product spec, architecture, eval strategy, demo script, sample data
docker/      API/web Dockerfiles and PostgreSQL pgvector init
scripts/     Local development notes
```

Core layers:

- Frontend: Next.js, TypeScript, Tailwind, shadcn-style primitives, lucide icons, React Flow.
- Backend: Python, FastAPI, Pydantic settings/schemas, modular API routers.
- Database path: local SQLite implementation for fast checkpoints plus PostgreSQL/pgvector-ready
  models and Docker infrastructure.
- Retrieval: deterministic local embeddings and hybrid keyword/vector scoring.
- Workflow engine: named deterministic workflows with trace linkage, designed to later swap in
  LangGraph or OpenAI Agents SDK.
- Code intelligence: AST/heuristic parser, graph builder, deterministic risk analyzer.
- Privacy and trust: local permission scopes, redaction, export, forget controls, and local-only mode.
- Knowledge graph: deterministic graph builder over profile, memory, journals, repos, code, and
  decisions.
- Simulation and evaluation: rubric-based drills and per-output self-evaluation.
- Plugins/models: capability registry plus cloud/local model provider options.
- Observability: internal trace records for inputs, retrieved memories, tools, outputs, latency,
  assumptions, errors, and steps.
- Approvals: preview, approve/reject, action audit, artifact records, and trace logs.

See `docs/architecture.md` for diagrams and entity details.

## Tech Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, lucide-react, React Flow.
- Backend: FastAPI, Pydantic, Python.
- Database: PostgreSQL + pgvector in Docker Compose; local SQLite-backed store for this checkpoint.
- Background-ready infrastructure: Redis in Docker Compose.
- AI provider: pluggable provider settings, deterministic local engine currently used for offline
  verification.
- Code intelligence: Python AST, TypeScript/JavaScript heuristics, optional tree-sitter/networkx
  detection for future expansion.

## Screenshots

Recommended demo screenshots:

- Command Center: dashboard metrics, priorities, projects, pending approvals, and voice panel.
- Code Intelligence: React Flow graph, searchable symbols, and risk report.
- Actions: proposed artifact preview, approve/reject controls, audit history, and generated artifact.
- Traces: run detail with evidence, steps, assumptions, latency, and output.
- Evals: prompt coverage and latest evaluation results.

Capture notes are in `docs/demo-video-script.md`; local screenshots can be saved under
`docs/screenshots/` after running the app.

## Quickstart

```bash
cp .env.example .env
npm install
```

In one terminal:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn atlas_api.main:app --reload --port 8000
```

In another terminal:

```bash
npm run dev:web
```

Local URLs:

- Web: http://localhost:3000
- API health: http://localhost:8000/healthz
- API docs: http://localhost:8000/docs

Docker infrastructure:

```bash
docker compose up --build
```

## Validation

```bash
cd apps/api
ruff check atlas_api tests
pytest
```

```bash
npm run lint
npm run build:web
```

## Demo Flow

1. Open Command Center and show priorities, projects, approvals, traces, and weak areas.
2. Open Profile and save goals, target roles, skills, weak areas, stack, and learning priorities.
3. Upload a resume PDF and inspect structured education, experience, projects, skills, certifications,
   and achievements.
4. Create or search memory, then ask a grounded question such as "What should I learn next?"
5. Run `generate_resume_bullets` or `prepare_interview_answer` from Workflows.
6. Save a journal entry and inspect weekly summary, resume bullets, interview stories, and insights.
7. Upload a repository ZIP from Projects.
8. Open Code Intel, run analysis, search symbols, inspect the graph, and review risk evidence.
9. Open Privacy and show allowed folders, blocked folders, redaction preview, export, and forget.
10. Open Graph and Growth to show the personal knowledge graph, timeline, and skill tree.
11. Open Decisions and store a technical decision with alternatives and tradeoffs.
12. Open Simulator and answer a system design or incident scenario.
13. Open Actions, propose an auto-demo pack, approve it, and inspect the artifact/audit log.
14. Open Traces, Evals, and Plugins to verify evidence, self-checks, model modes, and plugin scopes.

## What Makes Atlas Different

- Context-aware, not generic: personal memory, resume, journal, project, and codebase evidence shape
  responses.
- Traceable by design: every AI-like operation stores inputs, evidence, assumptions, output, latency,
  and steps.
- Approval-gated tools: writes happen only after preview and explicit approval.
- Codebase-aware: Atlas can inspect repositories through symbols, graphs, and deterministic risk
  checks.
- Trust-aware: Atlas has privacy scopes, redaction, export, forget controls, and self-evaluation.
- Growth-aware: Atlas turns work logs and decisions into a timeline, skill map, and interview drills.
- Product-shaped UI: dedicated surfaces for memory, workflows, code intelligence, actions, traces,
  and evaluations.

## Future Roadmap

- OpenAI embeddings and model calls behind provider policy.
- LangGraph or OpenAI Agents SDK for resumable multi-step agent workflows.
- Full tree-sitter grammars for richer symbol extraction and call graphs.
- Remote GitHub API integration after approval gates.
- Authentication, encrypted local secrets, and connector permissions.
- Background worker ingestion using Redis and a job queue.
- Claim-level citation scoring and golden-set eval fixtures.
- Deeper plugin SDK with versioned manifests and isolated tool execution.

## Resume Bullet

Built Atlas, a personal AI operating system that unifies memory, code intelligence, workflow
automation, approval-gated tool execution, and traceable agent reasoning to assist with engineering
work, learning, career planning, and daily productivity.
