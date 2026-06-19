import pytest
from fastapi.testclient import TestClient

from atlas_api.main import app
from atlas_api.services.tiny_database import TinyAtlasDatabase

client = TestClient(app)


def test_tiny_database_crud_and_explain() -> None:
    db = TinyAtlasDatabase()
    db.create_table("runs", ["id", "kind", "status"], primary_key="id")

    db.insert("runs", {"id": "run_1", "kind": "eval", "status": "pending"})
    db.update("runs", "run_1", {"status": "completed"})

    assert db.get("runs", "run_1") == {
        "id": "run_1",
        "kind": "eval",
        "status": "completed",
    }
    assert db.where("runs", kind="eval")[0]["id"] == "run_1"
    assert db.delete("runs", "run_1") is True
    assert db.scan("runs") == []

    explain = db.explain()
    assert explain["tables"]["runs"]["rows"] == 0
    assert explain["wal_entries"] == 4
    assert explain["index_type"] == "hash map primary-key index"


def test_tiny_database_rejects_bad_rows() -> None:
    db = TinyAtlasDatabase()
    db.create_table("memories", ["id", "title"])

    with pytest.raises(ValueError):
        db.insert("memories", {"id": "mem_1"})

    with pytest.raises(ValueError):
        db.insert("memories", {"id": "mem_1", "title": "Atlas", "extra": True})


def test_labs_api_exposes_three_portfolio_tracks() -> None:
    response = client.get("/api/labs")

    assert response.status_code == 200
    body = response.json()
    track_ids = {track["id"] for track in body["tracks"]}
    assert "tiny_database_from_scratch" in track_ids
    assert "local_code_intelligence_engine" in track_ids
    assert "end_to_end_ml_platform_lite" in track_ids
    assert body["tiny_database_demo"]["row_count"] == 2
    assert "systems portfolio" in body["portfolio_pitch"]
