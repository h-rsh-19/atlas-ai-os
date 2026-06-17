# Atlas Demo Video Script

## 60-90 Second Recruiter Cut

Narration:

"Here is Atlas, a local-first personal AI operating system for engineering work, learning, and career
growth. I seed the demo so the full product loop is visible: resume/profile context, memory,
repository analysis, workflow output, approval, artifact, and trace.

The key thing is trust. Atlas is not just a chat page. It shows the current runtime mode, generated
artifact, resume bullet, and every step in the golden path. The provider health page makes model
state explicit: deterministic fallback is active, OpenAI configuration is visible, and local
Ollama/vLLM endpoints are checked.

On traces, every AI-style run exposes inputs, prompt version, model/provider state, assumptions,
latency, tool calls, and outputs. On code intelligence, Atlas turns a repository into symbols, graph
relationships, and risk evidence. On actions, writes are previewed, approved, turned into real
artifacts, and audited.

The point of Atlas is realistic AI product engineering: personal context, code intelligence,
workflow automation, provider abstraction, approvals, and traceability in one polished system."

## 0:00 - Open Demo

Show the golden-flow page: resume upload, profile/goals, memory retrieval, repo upload, code
analysis, workflow, approval, artifact, and trace. Point out the current mode badge:
local deterministic prototype with LLM-ready architecture.

Narration: "Atlas is an ambitious personal AI OS, and this checkpoint is honest about where it is:
a local deterministic prototype with provider-ready architecture. The demo has one smooth story."

Click `Seed Demo` if the local state is empty. Show blockers, guided buttons, and `Copy Script`.

## 0:45 - Add Personal Context

Open Resume and show parsed structured sections. Then open Profile and show goals, target roles,
skills, weak areas, preferred stack, and learning priorities.

Narration: "Atlas starts from the user's own context and stores memory with citations."

## 1:30 - Ask A Grounded Question

Open Memory or Command and ask, "What should I learn next?" Show cited retrieved memories and trace ID.

Narration: "Answers are grounded in stored evidence and every run is traceable."

## 2:15 - Run A Workflow

Open Workflows and run `generate_resume_bullets` or `prepare_interview_answer`. Show steps, outputs,
and trace linkage.

Narration: "Workflows are named operations with inputs, outputs, status, and trace steps."

## 3:00 - Show Privacy And Knowledge

Open Privacy and show allowed folders, blocked folders, redaction preview, memory export, and forget.
Open Knowledge Graph and show relationships such as Atlas -> uses -> FastAPI and decisions -> relates
to -> backend.

Narration: "Atlas is local-first and evidence-based. The privacy controls are visible, and memory is
more than vector search: it becomes a personal knowledge graph."

## 4:00 - Growth And Decisions

Open Growth and show Timeline of You plus the skill tree. Open Decisions and store a technical
decision with alternatives, tradeoffs, reason, and result-later field.

Narration: "Atlas tracks the user's engineering growth over time and turns decisions into reusable
learning evidence."

## 5:00 - Ingest And Analyze Code

Open Projects, upload a repository ZIP, then open Code Intel and click Analyze. Show symbols, graph,
and deterministic risks.

Narration: "Atlas understands codebases through static analysis, dependency graphs, symbol extraction,
and evidence-linked risk checks."

## 6:00 - Simulator And Self-Evaluation

Open Simulator, start a system design or incident drill, answer it, and show rubric feedback. Open
Evals and run a self-check on an answer.

Narration: "Atlas can simulate realistic interview and production scenarios, then evaluate the answer
for structure and grounding."

## 7:00 - Approval-Gated Action

Open Actions, propose `generate_auto_demo_pack`, inspect the preview, approve it, then show the
artifact and trace.

Narration: "Atlas can produce real artifacts, but writes are explicit, previewed, approved, and audited."

## 8:00 - Plugins, Models, Evals And Close

Open Plugins and show permission scopes plus cloud/local model providers. Open Evals, run the suite,
and show pass/needs-data results.

Narration: "The evaluation suite checks retrieval, citations, workflow reliability, codebase Q&A, and
hallucination resistance. Atlas is built like an early product, not a throwaway chatbot."
