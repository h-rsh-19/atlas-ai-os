from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from atlas_api.core.config import get_settings


def now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:14]}"


def encode_json(value: Any) -> str:
    return json.dumps(value, default=str)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[4]


def artifact_dir() -> Path:
    settings = get_settings()
    configured = Path(settings.artifact_dir)
    if configured.is_absolute():
        return configured
    return workspace_root() / configured


def slug(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean[:72] or "atlas-artifact"


def default_redaction_patterns() -> list[str]:
    return [
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9_\-]{8,}",
        r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
    ]


def skill_category(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["fastapi", "backend", "api", "python"]):
        return "Backend"
    if any(term in lower for term in ["agent", "llm", "retrieval", "pgvector", "openai"]):
        return "AI Agents"
    if any(term in lower for term in ["ml", "model", "embedding", "evaluation"]):
        return "ML Systems"
    if any(term in lower for term in ["postgres", "sql", "database", "redis"]):
        return "Databases"
    if any(term in lower for term in ["docker", "devops", "deploy", "kubernetes"]):
        return "DevOps"
    if any(term in lower for term in ["system design", "distributed"]):
        return "System Design"
    if any(term in lower for term in ["dsa", "algorithm", "data structure"]):
        return "DSA"
    if any(term in lower for term in ["communication", "interview", "writing", "resume"]):
        return "Communication"
    return "Engineering"


def dependency_filenames() -> set[str]:
    return {
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "requirements.txt",
        "poetry.lock",
        "dockerfile",
        "docker-compose.yml",
        "go.mod",
        "cargo.toml",
        "pom.xml",
    }


def strip_zip_root(path: str) -> str:
    clean = path.strip("/")
    parts = clean.split("/")
    if len(parts) > 1:
        return "/".join(parts[1:])
    return clean


def ignored_repo_path(path: str) -> bool:
    ignored_parts = {".git", "node_modules", ".next", "__pycache__", ".venv", "dist", "build"}
    return any(part in ignored_parts for part in path.split("/"))


def is_text_path(path: str) -> bool:
    return Path(path).suffix.lower() in {
        ".md",
        ".txt",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".json",
        ".toml",
        ".yml",
        ".yaml",
        ".css",
        ".html",
        ".go",
        ".rs",
        ".java",
    }


def language_for_path(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".md": "Markdown",
        ".json": "JSON",
        ".css": "CSS",
        ".html": "HTML",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".sql": "SQL",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
    }.get(suffix)
