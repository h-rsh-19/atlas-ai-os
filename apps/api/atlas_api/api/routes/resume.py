from fastapi import APIRouter, Query, Request, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import ResumeProfile, ResumeUploadResponse
from atlas_api.services.resume_parser import extract_pdf_text, structure_resume
from atlas_api.services.store import store

router = APIRouter()


@router.get("/latest", response_model=ResumeProfile | None)
def latest_resume() -> ResumeProfile | None:
    return store.latest_resume()


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    request: Request,
    filename: str = Query(default="resume.pdf", min_length=1),
) -> ResumeUploadResponse:
    content_type = request.headers.get("content-type", "")
    if "pdf" not in content_type.lower() and not filename.lower().endswith(".pdf"):
        raise AtlasError(
            "Resume upload must be a PDF.",
            status_code=415,
            code="unsupported_resume_type",
        )

    pdf_bytes = await request.body()
    if not pdf_bytes:
        raise AtlasError("Uploaded resume PDF was empty.", status_code=400, code="empty_resume")

    raw_text = extract_pdf_text(pdf_bytes)
    if not raw_text.strip():
        raise AtlasError(
            "Atlas could not extract text from this PDF.",
            status_code=422,
            code="resume_text_extraction_failed",
        )

    structured = structure_resume(raw_text)
    resume, memories = store.store_resume(
        filename=filename,
        raw_text=raw_text,
        structured=structured,
    )
    return ResumeUploadResponse(resume=resume, created_memories=memories)
