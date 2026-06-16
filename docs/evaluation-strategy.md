# Atlas Evaluation Strategy

Atlas uses local deterministic evaluations first so the product can be tested without paid model calls.
The suite is intentionally evidence-oriented: it checks whether Atlas has enough stored context,
citations, traces, repo symbols, and approval history to support trustworthy AI workflows.

## Evaluation Categories

- Resume bullet quality: bullets should be action-oriented, technical, specific, and supported by
  resume, memory, or journal evidence.
- Memory retrieval accuracy: personal-context answers should retrieve relevant memories and show
  citations with titles and snippets.
- Codebase Q&A correctness: architecture summaries should cite indexed files, symbols, graph edges,
  and risk evidence.
- Workflow reliability: named workflows should complete, store outputs, and record trace steps.
- Citation quality: outputs should expose source snippets instead of unsupported claims.
- Hallucination checks: Atlas should admit when a fact is missing and recommend ingestion or profile
  updates instead of inventing details.
- Self-evaluation mode: any draft output can be checked for grounding, source usage, confidence,
  hallucination risk, and verification items before the user trusts it.

## Local Commands

```bash
cd apps/api
pytest
```

```bash
npm run lint
npm run build:web
```

The UI evaluation page calls:

```text
GET  /api/evals/prompts
POST /api/evals/run
GET  /api/evals
POST /api/self-eval
```

## Future Evaluation Work

- Add golden-answer fixtures for seeded profile, resume, journal, and repository data.
- Add LLM-as-judge only after deterministic checks pass.
- Track retrieval precision/recall over seeded memories.
- Score citation coverage by claim, not just by response.
- Add regression evals for code workflows after tree-sitter grammars are enabled.
