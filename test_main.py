import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from database import DB_PATH
from main import app


@pytest.fixture
def client():
    with TestClient(app) as http:
        yield http


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "brand": "RakitDigital",
        "founder": "MUHAMMAD MUFTI ZAKA",
    }


def test_create_project(client):
    response = client.post("/api/project/start", json={"client_name": "Toko Maju"})
    assert response.status_code == 200
    body = response.json()
    assert body["client_name"] == "Toko Maju"
    assert body["state"] == "LEAD"
    uuid.UUID(body["project_id"])


def test_valid_state_transition(client):
    created = client.post(
        "/api/project/start", json={"client_name": "Warung Bu Tini"}
    ).json()
    response = client.post(
        f"/api/project/{created['project_id']}/advance",
        json={"new_state": "DISCOVERY"},
    )
    assert response.status_code == 200
    assert response.json()["project_id"] == created["project_id"]
    assert response.json()["state"] == "DISCOVERY"


def test_invalid_state_transition(client):
    created = client.post(
        "/api/project/start", json={"client_name": "Kedai Kopi"}
    ).json()
    response = client.post(
        f"/api/project/{created['project_id']}/advance",
        json={"new_state": "QUOTED"},
    )
    assert response.status_code == 400


def test_chat_incomplete_is_not_json(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(
        f"/api/project/{created['project_id']}/chat",
        json={"message": "Halo mau bikin kasir"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NEED_MORE_INFO"
    reply = body["reply"]
    assert not reply.lstrip().startswith("{")
    assert "```json" not in reply


def test_chat_complete_spec_moves_to_quoted(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(
        f"/api/project/{created['project_id']}/chat",
        json={
            "message": (
                "Nama usaha: Toko Maju. "
                "Fitur: kasir, stok, laporan harian. "
                "Budget: 5000000."
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SPEC_COMPLETE"
    assert response.json()["state"] == "QUOTED"

    connection = sqlite3.connect(DB_PATH)
    try:
        row = connection.execute(
            "SELECT state FROM projects WHERE id = ?",
            (created["project_id"],),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row[0] == "QUOTED"


def _quoted_project(client, message: str | None = None) -> str:
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    client.post(
        f"/api/project/{created['project_id']}/chat",
        json={
            "message": message
            or "Nama usaha: Toko Maju. Fitur: kasir, stok. Budget: 5000000."
        },
    )
    return created["project_id"]


def _quote_row(quote_id: str):
    connection = sqlite3.connect(DB_PATH)
    try:
        return connection.execute(
            "SELECT final_price, discount_pct, status FROM quotes WHERE quote_id = ?",
            (quote_id,),
        ).fetchone()
    finally:
        connection.close()


def _project_state(project_id: str) -> str:
    connection = sqlite3.connect(DB_PATH)
    try:
        row = connection.execute(
            "SELECT state FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return row[0]


def test_generate_quote_matches_cost_plus_math(client):
    project_id = _quoted_project(client)
    response = client.post(f"/api/project/{project_id}/quote/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["hpp_breakdown"]["labor_hours"] == 16
    assert body["hpp_breakdown"]["infra_cost"] == 150000
    assert body["hpp_breakdown"]["labor_rate"] == 75000
    assert body["hpp_breakdown"]["total_hpp"] == 1350000
    assert body["margin_pct"] == 75
    assert body["final_price"] == 2350000
    assert body["version"] == 1
    assert body["status"] == "ACTIVE"


def test_generate_quote_rejects_non_quoted_state(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(f"/api/project/{created['project_id']}/quote/generate")
    assert response.status_code == 400


def test_discount_guardrails(client):
    project_id = _quoted_project(client)
    quote = client.post(f"/api/project/{project_id}/quote/generate").json()
    quote_id = quote["quote_id"]
    path = f"/api/project/{project_id}/quote/{quote_id}/discount"

    ten = client.post(path, json={"discount_pct": 10, "founder_approved": False})
    assert ten.status_code == 200
    assert ten.json()["discount_pct"] == 10
    assert ten.json()["final_price"] == 2115000

    blocked = client.post(path, json={"discount_pct": 15, "founder_approved": False})
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "ESCALATION_REQUIRED"
    assert _quote_row(quote_id)[0] == 2115000
    assert _quote_row(quote_id)[1] == 10

    approved = client.post(path, json={"discount_pct": 15, "founder_approved": True})
    assert approved.status_code == 200
    assert approved.json()["final_price"] == 1997500

    hard_cap = client.post(path, json={"discount_pct": 35, "founder_approved": True})
    assert hard_cap.status_code == 400
    assert hard_cap.json()["detail"] == "DISCOUNT_HARD_CAP"
    price, discount_pct, _status = _quote_row(quote_id)
    assert price == 1997500
    assert discount_pct == 15


def test_sign_latest_quote_and_reject_old_version(client):
    project_id = _quoted_project(client)
    first = client.post(f"/api/project/{project_id}/quote/generate").json()
    second = client.post(f"/api/project/{project_id}/quote/generate").json()
    assert first["version"] == 1
    assert second["version"] == 2
    assert second["status"] == "ACTIVE"

    stale = client.post(
        f"/api/project/{project_id}/sign",
        json={"quote_id": first["quote_id"]},
    )
    assert stale.status_code == 400
    assert _project_state(project_id) == "QUOTED"

    signed = client.post(
        f"/api/project/{project_id}/sign",
        json={"quote_id": second["quote_id"]},
    )
    assert signed.status_code == 200
    assert signed.json()["state"] == "SIGNED"
    assert signed.json()["quote_status"] == "ACCEPTED"
    assert _project_state(project_id) == "SIGNED"
    assert _quote_row(second["quote_id"])[2] == "ACCEPTED"


