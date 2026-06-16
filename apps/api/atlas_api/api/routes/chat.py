import time

from fastapi import APIRouter

from atlas_api.schemas import ChatRequest, ChatResponse, TraceStep
from atlas_api.services.store import store

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    profile = store.get_profile()
    hits = store.search_memories(payload.message, top_k=payload.top_k)
    citations = [citation for hit in hits for citation in hit.citations]

    answer = _build_grounded_answer(payload.message, payload.context or "", profile, hits)
    latency_ms = int((time.perf_counter() - started) * 1000)
    steps = [
        TraceStep(
            name="receive_input",
            status="completed",
            input={"message": payload.message, "context": payload.context},
            latency_ms=1,
        ),
        TraceStep(
            name="retrieve_memory",
            status="completed",
            input={"query": payload.message, "top_k": payload.top_k},
            output={"hits": len(hits)},
            tool_calls=[{"tool": "memory.search", "top_k": payload.top_k}],
            latency_ms=max(1, latency_ms),
        ),
        TraceStep(
            name="generate_answer",
            status="completed",
            output={"answer_chars": len(answer), "citations": len(citations)},
            latency_ms=2,
        ),
    ]
    trace = store.create_trace(
        interaction_type="chat",
        user_input=payload.message,
        retrieved_memories=hits,
        prompt_version="chat-grounded-v1",
        model_used="atlas-deterministic-chat-v1",
        tool_calls=[{"tool": "memory.search", "top_k": payload.top_k}],
        generated_output={"answer": answer, "citation_count": len(citations)},
        latency_ms=latency_ms,
        confidence=0.82 if hits else 0.45,
        assumptions=[
            "Local deterministic response used until an LLM provider is configured.",
            "Retrieved memories are treated as the source of truth for this answer.",
        ],
        steps=steps,
    )
    return ChatResponse(
        answer=answer,
        citations=citations[:6],
        retrieved_memories=hits,
        trace_id=trace.id,
    )


def _build_grounded_answer(message: str, context: str, profile, hits) -> str:
    lower = message.lower()
    evidence_lines = [f"- {hit.summary}" for hit in hits[:4]]
    evidence = "\n".join(evidence_lines) if evidence_lines else "- No stored evidence matched yet."

    if any(term in lower for term in ["learn next", "what should i learn", "learning"]):
        priorities = (
            profile.learning_priorities
            or profile.weaknesses
            or ["Add learning priorities to your profile"]
        )
        return (
            "Based on your stored profile and retrieved memories, "
            "your next learning focus should be:\n"
            + "\n".join(f"- {item}" for item in priorities[:5])
            + "\n\nWhy this is grounded:\n"
            + evidence
        )

    if "weak" in lower or "weakness" in lower:
        weaknesses = profile.weaknesses or ["No explicit weaknesses are stored yet."]
        return (
            "Your stored weak areas are:\n"
            + "\n".join(f"- {item}" for item in weaknesses)
            + "\n\nRelevant evidence:\n"
            + evidence
        )

    if "project" in lower and ("resume" in lower or "fit" in lower):
        return (
            "The strongest project fit from your current context is Atlas, because it demonstrates "
            "AI product thinking, backend architecture, full-stack execution, memory, retrieval, "
            "approvals, and traceability.\n\nRetrieved evidence:\n"
            + evidence
        )

    if "pitch" in lower or "interview" in lower:
        role = profile.role or "developer"
        targets = ", ".join(profile.target_roles[:3]) or "AI engineering roles"
        return (
            f"Interview pitch: I am a {role} targeting {targets}. My strongest story is Atlas: "
            "a private personal AI OS that connects profile, resume, memory, retrieval, approvals, "
            "and traceable workflows into one practical engineering system.\n\nCited support:\n"
            + evidence
        )

    if "resume bullet" in lower or "work log" in lower:
        source = context.strip() or message
        return (
            "Resume-ready bullets grounded in your supplied work log and stored context:\n"
            f"- Built {source[:110].strip()} with emphasis on measurable product outcomes.\n"
            "- Implemented source-backed AI workflows with citations and approvals.\n"
            "- Created a full-stack system spanning FastAPI, React, persistence, "
            "and observability.\n\nRelevant stored context:\n"
            + evidence
        )

    return (
        "Here is the grounded answer from your stored Atlas context:\n"
        + evidence
        + "\n\nAtlas avoided a generic answer by retrieving memories first "
        "and attaching citations to the response."
    )
