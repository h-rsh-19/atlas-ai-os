from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field


@dataclass
class StructuredResume:
    education: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "education": self.education,
            "experience": self.experience,
            "projects": self.projects,
            "skills": self.skills,
            "certifications": self.certifications,
            "achievements": self.achievements,
        }


SECTION_ALIASES = {
    "education": "education",
    "academic background": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "projects": "projects",
    "technical projects": "projects",
    "skills": "skills",
    "technical skills": "skills",
    "certifications": "certifications",
    "certification": "certifications",
    "achievements": "achievements",
    "awards": "achievements",
    "accomplishments": "achievements",
}


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(pdf_bytes)
        pages = [page.extract_text() or "" for page in reader.pages]
        extracted = "\n".join(page.strip() for page in pages if page.strip())
        if extracted:
            return extracted
    except Exception:
        pass

    return _fallback_extract_pdf_text(pdf_bytes)


def structure_resume(text: str) -> StructuredResume:
    sections = _split_sections(text)
    structured = StructuredResume()

    for section_key, lines in sections.items():
        if section_key == "skills":
            structured.skills = _dedupe(_split_skills(lines))
        elif hasattr(structured, section_key):
            setattr(structured, section_key, _dedupe(lines))

    if not structured.skills:
        structured.skills = _infer_skill_lines(text)
    if not structured.projects:
        structured.projects = _infer_project_lines(text)

    return structured


def _fallback_extract_pdf_text(pdf_bytes: bytes) -> str:
    streams = _extract_pdf_streams(pdf_bytes)
    text_parts: list[str] = []

    for stream in streams:
        decoded = stream.decode("latin-1", errors="ignore")
        text_parts.extend(_extract_text_operators(decoded))

    if text_parts:
        return "\n".join(part for part in text_parts if part.strip())

    decoded_pdf = pdf_bytes.decode("latin-1", errors="ignore")
    printable = re.findall(r"[A-Za-z][A-Za-z0-9 ,./+#:&()'\\-]{3,}", decoded_pdf)
    return "\n".join(_dedupe([item.strip() for item in printable]))


def _extract_pdf_streams(pdf_bytes: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in re.finditer(rb"(<<.*?>>)\s*stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.S):
        dictionary = match.group(1)
        stream = match.group(2)
        if b"/FlateDecode" in dictionary:
            try:
                stream = zlib.decompress(stream)
            except zlib.error:
                continue
        streams.append(stream)
    return streams


def _extract_text_operators(stream: str) -> list[str]:
    parts: list[str] = []
    for match in re.finditer(r"\((.*?)\)\s*Tj", stream, re.S):
        parts.append(_decode_pdf_string(match.group(1)))

    for match in re.finditer(r"\[(.*?)\]\s*TJ", stream, re.S):
        array_content = match.group(1)
        strings = re.findall(r"\((.*?)\)", array_content, re.S)
        if strings:
            parts.append("".join(_decode_pdf_string(value) for value in strings))

    return parts


def _decode_pdf_string(value: str) -> str:
    value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    value = value.replace(r"\n", "\n").replace(r"\r", "\n").replace(r"\t", "\t")
    return value.strip()


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "certifications": [],
        "achievements": [],
    }
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip(" \t-•")
        if not line:
            continue
        normalized = re.sub(r"[^a-zA-Z ]+", "", line).strip().lower()
        if normalized in SECTION_ALIASES:
            current = SECTION_ALIASES[normalized]
            continue
        if current:
            sections[current].append(line)

    return sections


def _split_skills(lines: list[str]) -> list[str]:
    joined = ", ".join(lines)
    values = re.split(r"[,;|/]| and ", joined)
    return [value.strip(" .") for value in values if value.strip(" .")]


def _infer_skill_lines(text: str) -> list[str]:
    known = [
        "python",
        "fastapi",
        "typescript",
        "react",
        "next.js",
        "postgresql",
        "redis",
        "docker",
        "openai",
        "langgraph",
        "sqlalchemy",
        "tailwind",
        "tree-sitter",
    ]
    lower = text.lower()
    return [skill for skill in known if skill in lower]


def _infer_project_lines(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        compact = line.strip()
        if re.search(r"\b(project|built|implemented|developed|designed)\b", compact, re.I):
            candidates.append(compact)
    return _dedupe(candidates[:8])


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        compact = " ".join(value.split())
        key = compact.lower()
        if compact and key not in seen:
            seen.add(key)
            output.append(compact)
    return output
