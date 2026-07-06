# Atlas Recruiter Walkthrough

Atlas is the flagship project in this profile. It is built to show full-stack product engineering,
AI system design, local-first privacy, traceability, and practical code intelligence in one working
app.

## 2-Minute Review Path

1. Start with the README badges and screenshots.
2. Watch `docs/screenshots/atlas-demo-walkthrough.webm`.
3. Open `docs/screenshots/01-demo-flow.png` to see the golden product loop.
4. Open `docs/screenshots/04-code-intelligence.png` to see repository analysis, symbols, graph
   relationships, and risk evidence.
5. Open `docs/screenshots/03-traces.png` and `docs/screenshots/05-actions.png` to see traceability
   and approval-gated writes.
6. Read `docs/architecture.md` if you want the deeper service and entity model.

## What To Notice

- Full-stack shape: Next.js/TypeScript frontend, FastAPI backend, local SQLite store, provider
  boundaries, CI, tests, screenshots, and demo video.
- AI product realism: deterministic local mode by default, LLM-ready provider interfaces, explicit
  fallback behavior, trace records, citations, and evaluations.
- Safety and trust: action proposals must be previewed and approved before artifact writes happen.
- Code intelligence: repository ingestion, Python AST parsing, TypeScript/JavaScript heuristics,
  symbol extraction, dependency graphing, and deterministic risk reports.
- Systems depth: Labs includes a tiny database proof, local code intelligence proof, and ML platform
  lite loop.

## Demo Story

The seeded demo follows one complete path:

```text
Resume and profile context
  -> Memory retrieval with evidence
  -> Repository/code analysis
  -> Workflow output
  -> Approval-gated artifact
  -> Trace and audit trail
  -> Labs systems proof
```

That matters because it is not only a UI shell. The demo shows how context, retrieval, workflows,
tool approvals, artifacts, and traces connect into a real product loop.

## Validation Signals

- GitHub Actions runs backend lint/tests, frontend lint/build, and Playwright E2E.
- `npm run capture:demo` regenerates the public screenshots and walkthrough video from the live local
  seeded demo.
- Backend tests cover privacy, graph, growth, simulator, plugins, providers, demo flow, code actions,
  labs, profile/memory/resume/chat, and health.

## Resume-Ready Summary

Built Atlas, a local-first personal AI operating system prototype with FastAPI, Next.js, SQLite,
code intelligence, workflow automation, approval-gated tools, trace logging, provider abstraction,
and evaluation workflows for engineering, learning, and career planning.
