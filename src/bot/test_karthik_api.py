"""Unit tests for Karthik RFP Analyzer FastAPI endpoints, Excel database repo, and architecture mapping."""
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

BOT_DIR = Path(__file__).resolve().parent
KARTHIK_DIR = BOT_DIR / "karthik_api"
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))
if str(KARTHIK_DIR) not in sys.path:
    sys.path.insert(0, str(KARTHIK_DIR))

try:
    from main import api_router, DIST  # noqa: E402
    from repo import Db, DB_PATH  # noqa: E402
except ImportError:
    from karthik_api.main import api_router, DIST  # noqa: E402
    from karthik_api.repo import Db, DB_PATH  # noqa: E402

TEST_HEADERS = {"X-User-Id": "yasaswini.k", "X-User-Name": "Yasaswini K"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    db = Db()
    if not db.tables.get("Proposals"):
        p = db.create_proposal("Sample proposal (template outputs)", "Acme", "yasaswini.k", seed_key="RFPAuthor")
        db.set_table(p["proposal_id"], "architecture_mapping", [
            {"current_state": "Legacy RDBMS", "target_state": "Azure SQL Hyperscale", "remark": "Automated sync pipeline"},
            {"current_state": "SOAP APIs", "target_state": "REST & GraphQL", "remark": "Microservices"},
        ])
        db.save()
    app = FastAPI(title="Test Karthik API")
    app.include_router(api_router)
    return TestClient(app)


def test_healthz_and_dist_built(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "dist" in data
    if data["dist"]:
        assert DIST.exists()


def test_api_meta_returns_user_identity_and_fields(client: TestClient) -> None:
    resp = client.get("/api/meta", headers=TEST_HEADERS)
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["user"]["user_id"] == "yasaswini.k"
    assert meta["user"]["display_name"] == "Yasaswini K"
    assert "Platform" in meta["user"].get("department", "")
    assert "architecture" in meta["tab_fields"]
    assert "architecture_mapping" in meta["tab_fields"]["architecture"]
    assert "current_state_architecture" in meta["tab_fields"]["architecture"]
    assert "target_architecture" in meta["tab_fields"]["architecture"]
    assert "roles" in meta["tab_fields"]["architecture"]


def test_api_meta_without_headers_returns_unknown_user(client: TestClient) -> None:
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["user"]["user_id"] == "unknown"
    assert meta["user"]["display_name"] == "Unknown"
    assert meta["user"].get("department", "") == ""


def test_list_proposals_from_excel_database(client: TestClient) -> None:
    resp = client.get("/api/proposals", headers=TEST_HEADERS)
    assert resp.status_code == 200
    proposals = resp.json()
    assert isinstance(proposals, list)
    assert len(proposals) > 0
    # Every proposal row has expected schema
    p0 = proposals[0]
    assert "proposal_id" in p0
    assert "name" in p0
    assert "client" in p0
    assert "owner_user_id" in p0
    assert "sections_ready" in p0


def test_get_proposal_bundle_and_architecture_mapping(client: TestClient) -> None:
    proposals_resp = client.get("/api/proposals", headers=TEST_HEADERS)
    proposals = proposals_resp.json()
    pid = proposals[0]["proposal_id"]

    resp = client.get(f"/api/proposals/{pid}", headers=TEST_HEADERS)
    assert resp.status_code == 200
    bundle = resp.json()
    assert bundle["proposal"]["proposal_id"] == pid
    assert "sections" in bundle
    assert "tables" in bundle
    assert "architecture_mapping" in bundle["tables"]
    assert "roles" in bundle["tables"]
    assert "work_breakdown" in bundle["tables"]
    assert "effort" in bundle
    assert "diagrams" in bundle
    assert "current_state_architecture" in bundle["diagrams"]
    assert "target_architecture" in bundle["diagrams"]


def test_compute_effort_formula_engine(client: TestClient) -> None:
    proposals_resp = client.get("/api/proposals", headers=TEST_HEADERS)
    pid = proposals_resp.json()[0]["proposal_id"]

    bundle_resp = client.get(f"/api/proposals/{pid}", headers=TEST_HEADERS)
    effort_state = bundle_resp.json()["effort"]["state"]

    resp = client.post(f"/api/proposals/{pid}/effort/compute", json={"state": effort_state}, headers=TEST_HEADERS)
    assert resp.status_code == 200
    computed = resp.json()
    assert "summary" in computed
    assert "wbs_total" in computed
    assert "effort_total" in computed
    assert "delta" in computed


def test_save_architecture_mapping_table(client: TestClient) -> None:
    proposals_resp = client.get("/api/proposals", headers=TEST_HEADERS)
    pid = proposals_resp.json()[0]["proposal_id"]

    sample_mapping = [
        {"current_state": "Legacy RDBMS", "target_state": "Azure SQL Hyperscale", "remark": "Automated sync pipeline"},
        {"current_state": "SOAP APIs", "target_state": "REST & GraphQL", "remark": "Microservices"},
    ]
    resp = client.put(f"/api/proposals/{pid}/tables/architecture_mapping", json={"rows": sample_mapping}, headers=TEST_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 2
    assert data["rows"][0]["target_state"] == "Azure SQL Hyperscale"
