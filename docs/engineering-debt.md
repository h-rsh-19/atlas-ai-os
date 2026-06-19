# Atlas Engineering Debt

## Store Composition

Current state: `AtlasStore` is a facade that uses service mixins for memory, workflow, trace, action,
code, privacy, and growth behavior. This reduced the original giant store file quickly while keeping
the route API stable.

Next upgrade: move from mixins to explicit composition, for example `store.memory.create(...)` with
shared database/session dependencies injected into each service.

## Database Migrations

Current state: local SQLite tables are created during `store.initialize()`. This is acceptable for v0
prototype velocity.

Next upgrade: add explicit migrations, ideally Alembic for relational schema changes plus a clear
local migration runner for SQLite development databases.

## Visual QA Checklist

Run after significant UI changes:

- `/`
- `/demo`
- `/memory`
- `/code`
- `/actions`
- `/traces`
- `/providers`

Check desktop and mobile widths, fallback/provider warnings, long text wrapping, graph rendering,
approval preview ergonomics, and trace detail readability.

Latest pass: browser DOM QA was run for `/demo`, `/traces`, `/memory`, `/code`, `/actions`,
`/providers`, plus mobile `/demo`. Console errors were clean and wrapping issues were fixed for the
new demo/provider/action surfaces. Playwright screenshots and a silent walkthrough video are captured
under `docs/screenshots/`.

## Real Provider Trial

Current local check: `ATLAS_OPENAI_API_KEY` is not configured and Ollama is not reachable on
`http://localhost:11434`, so a real provider trace was not recorded in this pass.

Next upgrade: run one OpenAI or Ollama chat through the provider layer, keep the generated trace, and
document the provider state in the README as a real-provider execution demo.

## Labs Follow-Ups

The new Labs surface adds a real TinyAtlasDatabase learning kernel, richer local code intelligence
metrics, and an ML-platform-lite proof track. The next serious upgrades are:

- Persist the tiny database operation log to JSONL and replay it on startup.
- Add secondary indexes, range scans, and query-plan explanations.
- Add Alembic migrations before expanding stored Labs progress.
- Add tree-sitter parsers and NetworkX centrality metrics for the code intelligence engine.
- Add dataset registry, model-run cost tracking, and provider policy tests for the ML platform loop.
