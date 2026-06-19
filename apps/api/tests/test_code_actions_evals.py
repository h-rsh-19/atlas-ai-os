from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from atlas_api.main import app

client = TestClient(app)


def test_code_analysis_extracts_symbols_graph_and_risks() -> None:
    project = _upload_repo()

    response = client.post(f"/api/code/analyze/{project['id']}")

    assert response.status_code == 200
    body = response.json()
    assert any(symbol["name"] == "plan_day" for symbol in body["symbols"])
    assert body["graph"]["nodes"]
    assert body["graph"]["edges"]
    assert body["graph"]["metrics"]["route_map"]
    assert body["graph"]["metrics"]["test_coverage"]["source_files"] >= 1
    assert body["graph"]["metrics"]["refactor_priorities"]
    assert body["risk_report"]["metrics"]["top_refactor_priorities"]
    assert body["risk_report"]["risks"]

    symbols_response = client.get(f"/api/code/symbols?project_id={project['id']}&query=plan")
    assert symbols_response.status_code == 200
    assert symbols_response.json()[0]["file_path"] == "apps/api/planner.py"


def test_code_workflow_uses_repo_analysis_with_file_citations() -> None:
    project = _upload_repo()
    client.post(f"/api/code/analyze/{project['id']}")

    response = client.post(
        "/api/workflows/run",
        json={
            "workflow_name": "architecture_summary",
            "inputs": {"project_id": project["id"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outputs"]["repository"] == project["name"]
    assert body["outputs"]["file_citations"]
    assert body["trace_id"]


def test_approval_action_previews_then_writes_artifact_after_approval() -> None:
    propose = client.post(
        "/api/actions",
        json={
            "tool_name": "create_task_list",
            "title": "Atlas next actions",
            "risk_level": "low",
            "inputs": {"topic": "code intelligence", "tasks": ["Run analysis"]},
        },
    )

    assert propose.status_code == 201
    action = propose.json()
    assert action["status"] == "pending"
    assert "Run analysis" in action["preview"]

    approved = client.post(f"/api/actions/{action['id']}/approve")

    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert body["artifact_path"]
    assert Path(body["artifact_path"]).exists()


def test_dashboard_and_evals_expose_operating_system_signals() -> None:
    dashboard = client.get("/api/dashboard")
    prompts = client.get("/api/evals/prompts")
    run = client.post("/api/evals/run")

    assert dashboard.status_code == 200
    assert "memories" in dashboard.json()["metrics"]
    assert prompts.status_code == 200
    assert len(prompts.json()) >= 6
    assert run.status_code == 200
    assert run.json()["results"]
    assert run.json()["trace_id"]


def _upload_repo() -> dict:
    archive = _minimal_zip(
        {
            "atlas/README.md": "# Atlas\nShort",
            "atlas/apps/api/planner.py": (
                "from atlas.memory import search\n\n"
                "def plan_day(goal):\n"
                "    TODO = 'tighten tests'\n"
                "    return search(goal)\n\n"
                "class Planner:\n"
                "    def run(self):\n"
                "        return plan_day('Atlas')\n"
            ),
            "atlas/apps/api/router.py": (
                "from fastapi import APIRouter\n"
                "router = APIRouter()\n\n"
                "@router.get('/plan')\n"
                "def get_plan():\n"
                "    return {'ok': True}\n"
            ),
            "atlas/apps/web/page.tsx": (
                "import { plan } from './plan'\n"
                "export default function Page() { return plan() }\n"
            ),
            "atlas/package.json": "{\"dependencies\":{\"next\":\"16.2.9\"}}",
        }
    )
    response = client.post(
        "/api/projects/zip?filename=atlas-code.zip",
        content=archive,
        headers={"content-type": "application/zip"},
    )
    assert response.status_code == 201
    return response.json()


def _minimal_zip(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()
