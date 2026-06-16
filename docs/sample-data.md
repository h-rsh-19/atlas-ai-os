# Atlas Sample Data

Use this data to seed a demo profile and show the product loop end to end.

## Profile

- Name: Atlas Builder
- Role: Student / Developer
- Current goals:
  - Build Atlas into a recruiter-impressive AI product.
  - Improve backend architecture and AI evaluation depth.
  - Turn project work into interview stories and resume bullets.
- Target roles:
  - AI Product Engineer
  - Backend Engineer
  - Full-stack AI Engineer
- Skills:
  - Python
  - FastAPI
  - TypeScript
  - React
  - PostgreSQL
  - Product thinking
- Weak areas:
  - Distributed systems interviews
  - Production AI evaluation
  - Deep codebase analysis
- Preferred stack:
  - Next.js
  - TypeScript
  - Tailwind
  - FastAPI
  - PostgreSQL
  - Redis
- Learning priorities:
  - pgvector retrieval
  - agent traces
  - approval-gated tools
  - tree-sitter code intelligence

## Journal Entry

- Built: Added code intelligence, graph visualization, risk analysis, and approval-gated artifacts.
- Problems: Needed useful deterministic analysis without depending on network installs.
- Decisions: Use Python AST plus TypeScript/JavaScript heuristics now, with optional tree-sitter later.
- Skills used:
  - FastAPI
  - TypeScript
  - React Flow
  - Product architecture
- Next tasks:
  - Add richer parser grammars.
  - Add seeded evaluation fixtures.
  - Add GitHub issue creation after approval.

## Demo Memory

Source title: Atlas design principle

Content:

```text
Atlas should avoid generic answers by retrieving personal profile, resume, project, journal, and
codebase evidence before producing plans or career artifacts. Any write action must be previewed,
approved, logged, and traceable.
```

## Decision

- Title: Use local-first privacy controls
- Decision: Atlas should expose allowed folders, blocked folders, redaction, memory export, and forget
  controls before adding external connectors.
- Alternatives:
  - Cloud-only assistant
  - Hidden local config
- Tradeoffs:
  - More UI and backend work
  - Stronger trust and recruiter signal
- Reason: A personal AI OS is only credible if users can inspect and control sensitive context.
- Tags:
  - privacy
  - architecture

## Simulator Answer Seed

Scenario: Design a personal AI OS.

Answer:

```text
I would split Atlas into frontend workspace, FastAPI backend, memory/retrieval, workflow engine,
approval-gated tool layer, trace logging, code intelligence, privacy service, and plugin registry.
I would keep local-first mode as the default, require approvals before writes, and store traces for
retrieval, tools, assumptions, and outputs. I would test retrieval grounding, citation quality, and
failure modes like missing evidence or stuck workflow runs.
```
