from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 1400, overlap: int = 160) -> list[str]:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(cleaned) <= max_chars:
        return [cleaned] if cleaned else []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        boundary = cleaned.rfind("\n", start, end)
        if boundary <= start + max_chars // 2:
            boundary = cleaned.rfind(". ", start, end)
        if boundary <= start:
            boundary = end

        chunk = cleaned[start:boundary].strip()
        if chunk:
            chunks.append(chunk)
        if boundary >= len(cleaned):
            break
        start = max(0, boundary - overlap)

    return chunks


def summarize_text(text: str, *, max_chars: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."
