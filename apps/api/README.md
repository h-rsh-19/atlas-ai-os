# Atlas API

FastAPI service for Atlas. The first checkpoint includes health checks, typed routing, settings, logging, database connection plumbing, and domain models for memory, workflows, traces, approvals, projects, and code intelligence.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn atlas_api.main:app --reload --port 8000
```

## Test

```bash
pytest
```
