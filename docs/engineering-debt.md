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
new demo/provider/action surfaces. Screenshot capture still needs a follow-up in an environment where
the browser screenshot or macOS display capture path is available.
