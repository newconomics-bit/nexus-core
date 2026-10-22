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
    assert body["final_price"] == 2400000
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
    assert ten.json()["final_price"] == 2160000

    blocked = client.post(path, json={"discount_pct": 15, "founder_approved": False})
    assert blocked.status_code == 202
    assert blocked.json()["status"] == "ESCALATED"
    assert blocked.json()["approval_id"]
    assert _quote_row(quote_id)[0] == 2160000
    assert _quote_row(quote_id)[1] == 10

    approved = client.post(path, json={"discount_pct": 15, "founder_approved": True})
    assert approved.status_code == 200
    assert approved.json()["final_price"] == 2040000

    hard_cap = client.post(path, json={"discount_pct": 35, "founder_approved": True})
    assert hard_cap.status_code == 400
    assert hard_cap.json()["detail"] == "DISCOUNT_HARD_CAP"
    price, discount_pct, _status = _quote_row(quote_id)
    assert price == 2040000
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


def _fresh_quote(client):
    project_id = _quoted_project(client)
    quote = client.post(f"/api/project/{project_id}/quote/generate").json()
    return project_id, quote


def test_margin_ceil_rounds_price_up(client):
    _project_id, quote = _fresh_quote(client)
    assert quote["hpp_breakdown"]["total_hpp"] == 1350000
    assert quote["final_price"] == 2400000


def test_discount_15_without_approval_escalates(client):
    project_id, quote = _fresh_quote(client)
    response = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "ESCALATED"
    approval_id = body["approval_id"]
    assert _quote_row(quote["quote_id"])[0] == 2400000
    assert _quote_row(quote["quote_id"])[1] == 0

    pending = client.get("/api/approvals/pending").json()
    match = next(item for item in pending if item["approval_id"] == approval_id)
    assert match["status"] == "PENDING"
    assert match["payload"]["discount_pct"] == 15
    assert match["payload"]["final_price_before"] == 2400000
    assert match["payload"]["final_price_after"] == 2040000


def test_decide_approved_applies_discount(client):
    project_id, quote = _fresh_quote(client)
    escalated = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    ).json()
    approval_id = escalated["approval_id"]
    decided = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"decision": "APPROVED", "decided_by": "MUHAMMAD MUFTI ZAKA"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "APPROVED"
    assert decided.json()["final_price"] == 2040000
    assert _quote_row(quote["quote_id"])[0] == 2040000
    assert _quote_row(quote["quote_id"])[1] == 15


def test_decide_rejected_leaves_quote(client):
    project_id, quote = _fresh_quote(client)
    escalated = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    ).json()
    decided = client.post(
        f"/api/approvals/{escalated['approval_id']}/decide",
        json={"decision": "REJECTED", "decided_by": "MUHAMMAD MUFTI ZAKA"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "REJECTED"
    assert decided.json()["final_price"] == 2400000
    assert _quote_row(quote["quote_id"])[0] == 2400000
    assert _quote_row(quote["quote_id"])[1] == 0


def test_decide_twice_returns_409(client):
    project_id, quote = _fresh_quote(client)
    escalated = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    ).json()
    path = f"/api/approvals/{escalated['approval_id']}/decide"
    body = {"decision": "APPROVED", "decided_by": "MUHAMMAD MUFTI ZAKA"}
    first = client.post(path, json=body)
    second = client.post(path, json=body)
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "APPROVAL_ALREADY_DECIDED"


def test_pending_approvals_lists_open_requests(client):
    project_id, quote = _fresh_quote(client)
    escalated = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    ).json()
    response = client.get("/api/approvals/pending")
    assert response.status_code == 200
    pending = response.json()
    assert any(
        item["approval_id"] == escalated["approval_id"] and item["status"] == "PENDING"
        for item in pending
    )


def test_telegram_webhook_callback_decides_approval(client):
    project_id, quote = _fresh_quote(client)
    escalated = client.post(
        f"/api/project/{project_id}/quote/{quote['quote_id']}/discount",
        json={"discount_pct": 15, "founder_approved": False},
    ).json()
    approval_id = escalated["approval_id"]
    response = client.post(
        "/api/telegram/webhook",
        json={
            "update_id": 1,
            "callback_query": {
                "id": "cb-mock-1",
                "data": f"APPROVED|{approval_id}",
                "from": {"id": 1, "first_name": "MUHAMMAD MUFTI ZAKA"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["final_price"] == 2040000
    assert _quote_row(quote["quote_id"])[0] == 2040000


def _signed_project(client) -> str:
    project_id = _quoted_project(client)
    quote = client.post(f"/api/project/{project_id}/quote/generate").json()
    signed = client.post(
        f"/api/project/{project_id}/sign",
        json={"quote_id": quote["quote_id"]},
    )
    assert signed.status_code == 200
    assert signed.json()["state"] == "SIGNED"
    return project_id


def test_build_start_rejects_non_signed_state(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(f"/api/project/{created['project_id']}/build/start")
    assert response.status_code == 400


def test_build_start_signed_creates_tasks(client):
    project_id = _signed_project(client)
    response = client.post(f"/api/project/{project_id}/build/start")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["state"] == "BUILDING"
    tasks = body["tasks"]
    assert len(tasks) >= 3
    kinds = {t["kind"] for t in tasks}
    assert "FRONTEND" in kinds
    assert "BACKEND" in kinds
    assert "DATABASE" in kinds
    for t in tasks:
        assert t["status"] == "PENDING"
        assert "task_id" in t


def test_build_run_mock_mode_completes(client):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")
    response = client.post(f"/api/project/{project_id}/build/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY_FOR_AUDIT"
    assert body["project_state"] == "AUDITING"
    submission = body["submission"]
    assert submission["status"] == "READY_FOR_AUDIT"
    assert submission["task_count"] >= 3
    assert len(submission["artifact_ids"]) == submission["task_count"]


def test_build_status_shows_progress(client):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")
    response = client.get(f"/api/project/{project_id}/build/status")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["project_state"] == "BUILDING"
    assert body["total_tasks"] >= 3
    assert body["pending"] == body["total_tasks"]
    assert body["done"] == 0
    assert body["failed"] == 0

    client.post(f"/api/project/{project_id}/build/run")
    response = client.get(f"/api/project/{project_id}/build/status")
    assert response.status_code == 200
    body = response.json()
    assert body["project_state"] == "AUDITING"
    assert body["pending"] == 0
    assert body["done"] == body["total_tasks"]
    assert body["failed"] == 0


def test_circuit_breaker_blocks_after_3_failures(client, monkeypatch):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")

    async def always_fail(*args, **kwargs):
        raise Exception("LLM failed")

    import agents.engineering_build as eng
    monkeypatch.setattr(eng, "call_llm", always_fail)

    response = client.post(f"/api/project/{project_id}/build/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["project_state"] == "BLOCKED"
    assert "failed after 3 attempts" in body["submission"]["status"]

    status = client.get(f"/api/project/{project_id}/build/status").json()
    assert status["project_state"] == "BLOCKED"
    assert status["failed"] >= 1
    assert status["done"] == 0



