from fastapi import APIRouter, Query, Request, status

from atlas_api.core.errors import AtlasError
from atlas_api.schemas import RepoConnectRequest, RepoProject
from atlas_api.services.store import store

router = APIRouter()


@router.get("", response_model=list[RepoProject])
def list_projects() -> list[RepoProject]:
    return store.list_repos()


@router.post("/github", response_model=RepoProject, status_code=status.HTTP_201_CREATED)
def connect_github_repo(payload: RepoConnectRequest) -> RepoProject:
    if "github.com" not in payload.github_url.lower():
        raise AtlasError(
            "Expected a GitHub repository URL.",
            status_code=400,
            code="invalid_repo_url",
        )
    return store.connect_github_repo(payload.github_url)


@router.post("/zip", response_model=RepoProject, status_code=status.HTTP_201_CREATED)
async def ingest_repo_zip(
    request: Request,
    filename: str = Query(default="repository.zip", min_length=1),
) -> RepoProject:
    if not filename.lower().endswith(".zip"):
        raise AtlasError(
            "Repository upload must be a ZIP file.",
            status_code=415,
            code="invalid_zip",
        )
    zip_bytes = await request.body()
    if not zip_bytes:
        raise AtlasError("Uploaded ZIP was empty.", status_code=400, code="empty_zip")
    try:
        return store.ingest_repo_zip(filename, zip_bytes)
    except Exception as exc:
        raise AtlasError(
            "Could not parse repository ZIP.",
            status_code=422,
            code="zip_parse_failed",
        ) from exc
