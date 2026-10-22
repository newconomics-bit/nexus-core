import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from database import DB_PATH
from main import app


API_KEY = "dev-secret-key-change-in-production"


@pytest.fixture
def client():
    with TestClient(app) as http:
        http.headers.update({"X-API-Key": API_KEY})
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
                "data": f"APPROVE|{approval_id}",
                "from": {"id": 123456789, "first_name": "MUHAMMAD MUFTI ZAKA"},
            },
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "dev-webhook-secret-change-in-production"},
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


def _audit_ready_project(client) -> str:
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")
    client.post(f"/api/project/{project_id}/build/run")
    return project_id


def test_audit_run_rejects_non_auditing_state(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(f"/api/project/{created['project_id']}/audit/run")
    assert response.status_code == 400


def test_audit_clean_artifacts_passed(client):
    project_id = _audit_ready_project(client)
    response = client.post(f"/api/project/{project_id}/audit/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PASSED"
    assert body["cycle"] == 1
    assert len(body["findings"]) == 0

    state = _project_state(project_id)
    assert state == "APPROVED"

    reports = client.get(f"/api/project/{project_id}/audit/reports").json()
    assert len(reports) == 1
    assert reports[0]["cycle"] == 1
    assert reports[0]["status"] == "PASSED"


def test_audit_finds_critical_password(client, monkeypatch):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")

    async def dirty_backend(*args, **kwargs):
        from models import BuildArtifact, TaskStatus
        import uuid
        from datetime import datetime, timezone
        task = args[0]
        spec = args[1]
        artifact = BuildArtifact(
            artifact_id=str(uuid.uuid4()),
            project_id=task.project_id,
            task_id=task.task_id,
            filename="backend_feature.py",
            content="password = 'admin123'\napi_key = 'secret123'\nprint('hello')",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_build_artifact
        await save_build_artifact(artifact)
        task.status = TaskStatus.DONE
        task.artifact_id = artifact.artifact_id
        from database import save_build_task
        await save_build_task(task)
        return artifact

    import agents.engineering_build as eng
    monkeypatch.setattr(eng, "execute_task", dirty_backend)

    client.post(f"/api/project/{project_id}/build/run")
    response = client.post(f"/api/project/{project_id}/audit/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["cycle"] == 1
    assert any(f["severity"] == "CRITICAL" for f in body["findings"])
    assert any("password" in f["description"].lower() for f in body["findings"])

    state = _project_state(project_id)
    assert state == "BUILDING"


def test_audit_rework_loop_three_cycles_blocked(client, monkeypatch):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")

    async def dirty_backend(*args, **kwargs):
        from models import BuildArtifact, TaskStatus
        import uuid
        from datetime import datetime, timezone
        task = args[0]
        spec = args[1]
        artifact = BuildArtifact(
            artifact_id=str(uuid.uuid4()),
            project_id=task.project_id,
            task_id=task.task_id,
            filename="backend_feature.py",
            content="password = 'admin123'\napi_key = 'secret123'\nprint('hello')",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_build_artifact
        await save_build_artifact(artifact)
        task.status = TaskStatus.DONE
        task.artifact_id = artifact.artifact_id
        from database import save_build_task
        await save_build_task(task)
        return artifact

    import agents.engineering_build as eng
    monkeypatch.setattr(eng, "execute_task", dirty_backend)

    for cycle in range(1, 4):
        build_resp = client.post(f"/api/project/{project_id}/build/run")
        assert build_resp.status_code == 200

        audit_resp = client.post(f"/api/project/{project_id}/audit/run")
        assert audit_resp.status_code == 200
        body = audit_resp.json()
        assert body["cycle"] == cycle

    assert body["status"] == "ESCALATED"
    assert body["cycle"] == 3

    state = _project_state(project_id)
    assert state == "BLOCKED"

    pending = client.get("/api/approvals/pending").json()
    qa_esc = [a for a in pending if a["type"] == "QA_ESCALATION" and a["project_id"] == project_id]
    assert len(qa_esc) == 1
    assert qa_esc[0]["status"] == "PENDING"


def test_audit_medium_only_passed(client, monkeypatch):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")

    async def medium_artifact(*args, **kwargs):
        from models import BuildArtifact, TaskStatus
        import uuid
        from datetime import datetime, timezone
        task = args[0]
        spec = args[1]
        artifact = BuildArtifact(
            artifact_id=str(uuid.uuid4()),
            project_id=task.project_id,
            task_id=task.task_id,
            filename="config.py",
            content="host = '0.0.0.0'\nport = 8000",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_build_artifact
        await save_build_artifact(artifact)
        task.status = TaskStatus.DONE
        task.artifact_id = artifact.artifact_id
        from database import save_build_task
        await save_build_task(task)
        return artifact

    import agents.engineering_build as eng
    monkeypatch.setattr(eng, "execute_task", medium_artifact)

    client.post(f"/api/project/{project_id}/build/run")
    response = client.post(f"/api/project/{project_id}/audit/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PASSED"
    assert body["cycle"] == 1
    assert any(f["severity"] == "MEDIUM" for f in body["findings"])
    assert not any(f["severity"] in ("CRITICAL", "HIGH") for f in body["findings"])

    state = _project_state(project_id)
    assert state == "APPROVED"


def test_audit_reports_ordered_by_cycle(client, monkeypatch):
    project_id = _signed_project(client)
    client.post(f"/api/project/{project_id}/build/start")

    async def dirty_backend(*args, **kwargs):
        from models import BuildArtifact, TaskStatus
        import uuid
        from datetime import datetime, timezone
        task = args[0]
        spec = args[1]
        artifact = BuildArtifact(
            artifact_id=str(uuid.uuid4()),
            project_id=task.project_id,
            task_id=task.task_id,
            filename="backend_feature.py",
            content="password = 'admin123'",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_build_artifact
        await save_build_artifact(artifact)
        task.status = TaskStatus.DONE
        task.artifact_id = artifact.artifact_id
        from database import save_build_task
        await save_build_task(task)
        return artifact

    import agents.engineering_build as eng
    monkeypatch.setattr(eng, "execute_task", dirty_backend)

    for _ in range(3):
        client.post(f"/api/project/{project_id}/build/run")
        client.post(f"/api/project/{project_id}/audit/run")

    reports = client.get(f"/api/project/{project_id}/audit/reports").json()
    assert len(reports) == 3
    assert reports[0]["cycle"] == 1
    assert reports[1]["cycle"] == 2
    assert reports[2]["cycle"] == 3
    assert reports[0]["status"] == "FAILED"
    assert reports[1]["status"] == "FAILED"
    assert reports[2]["status"] == "ESCALATED"


def _approved_project(client) -> str:
    project_id = _audit_ready_project(client)
    client.post(f"/api/project/{project_id}/audit/run")
    assert _project_state(project_id) == "APPROVED"
    return project_id


def test_deploy_request_rejects_non_approved_state(client):
    created = client.post("/api/project/start", json={"client_name": "Toko Maju"}).json()
    response = client.post(
        f"/api/project/{created['project_id']}/deploy/request",
        json={"domain_choice": "HOSTED"},
    )
    assert response.status_code == 400


def test_deploy_request_hosted_generates_url_and_approval(client):
    project_id = _approved_project(client)
    response = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "HOSTED"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert "deployment_id" in body
    assert "approval_id" in body

    pending = client.get("/api/approvals/pending").json()
    dep_approvals = [a for a in pending if a["type"] == "DEPLOY_PRODUCTION" and a["project_id"] == project_id]
    assert len(dep_approvals) == 1
    assert dep_approvals[0]["payload"]["hosted_url"].endswith(".rakitdigital.app")
    assert dep_approvals[0]["payload"]["domain_choice"] == "HOSTED"


def test_deploy_request_custom_requires_url(client):
    project_id = _approved_project(client)
    response = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "CUSTOM"},
    )
    assert response.status_code == 400


def test_deploy_request_custom_generates_approval(client):
    project_id = _approved_project(client)
    response = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "CUSTOM", "custom_domain_url": "https://myapp.example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert "deployment_id" in body
    assert "approval_id" in body

    pending = client.get("/api/approvals/pending").json()
    dep_approvals = [a for a in pending if a["type"] == "DEPLOY_PRODUCTION" and a["project_id"] == project_id]
    assert len(dep_approvals) == 1
    assert dep_approvals[0]["payload"]["custom_domain_url"] == "https://myapp.example.com"
    assert dep_approvals[0]["payload"]["domain_choice"] == "CUSTOM"


def test_deploy_approve_full_flow(client):
    project_id = _approved_project(client)
    deploy_resp = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "HOSTED"},
    )
    assert deploy_resp.status_code == 200
    deployment_id = deploy_resp.json()["deployment_id"]
    approval_id = deploy_resp.json()["approval_id"]

    decide_resp = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"decision": "APPROVED", "decided_by": "MUHAMMAD MUFTI ZAKA"},
    )
    assert decide_resp.status_code == 200
    body = decide_resp.json()
    assert body["status"] == "APPROVED"
    assert "deployment" in body
    assert body["deployment"]["status"] == "DEPLOYED"
    assert body["deployment"]["live_url"].endswith(".rakitdigital.app")

    state = _project_state(project_id)
    assert state == "SUBSCRIPTION"


def test_deploy_reject_keeps_approved_state(client):
    project_id = _approved_project(client)
    deploy_resp = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "CUSTOM", "custom_domain_url": "https://myapp.example.com"},
    )
    assert deploy_resp.status_code == 200
    deployment_id = deploy_resp.json()["deployment_id"]
    approval_id = deploy_resp.json()["approval_id"]

    decide_resp = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"decision": "REJECTED", "decided_by": "MUHAMMAD MUFTI ZAKA"},
    )
    assert decide_resp.status_code == 200
    body = decide_resp.json()
    assert body["status"] == "REJECTED"
    assert body["deployment_id"] == deployment_id

    state = _project_state(project_id)
    assert state == "APPROVED"

    pending = client.get("/api/approvals/pending").json()
    dep_approvals = [a for a in pending if a["type"] == "DEPLOY_PRODUCTION" and a["project_id"] == project_id]
    assert len(dep_approvals) == 0


def _deployed_project(client) -> str:
    project_id = _approved_project(client)
    deploy_resp = client.post(
        f"/api/project/{project_id}/deploy/request",
        json={"domain_choice": "HOSTED"},
    )
    assert deploy_resp.status_code == 200
    approval_id = deploy_resp.json()["approval_id"]
    decide_resp = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"decision": "APPROVED", "decided_by": "MUHAMMAD MUFTI ZAKA"},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["deployment"]["status"] == "DEPLOYED"
    assert _project_state(project_id) == "SUBSCRIPTION"
    return project_id


def test_billing_activate_subscription_on_deploy(client):
    project_id = _deployed_project(client)
    state = _project_state(project_id)
    assert state == "SUBSCRIPTION"

    invoices = client.get(f"/api/project/{project_id}/billing/invoices").json()
    assert len(invoices) == 1
    assert invoices[0]["status"] == "PENDING"
    assert invoices[0]["amount"] == 150000


def test_billing_mock_payment_creates_next_invoice(client):
    project_id = _deployed_project(client)
    assert _project_state(project_id) == "SUBSCRIPTION"

    invoices = client.get(f"/api/project/{project_id}/billing/invoices").json()
    invoice_id = invoices[0]["invoice_id"]

    webhook_resp = client.post(
        "/api/webhooks/payment/mock",
        json={"invoice_id": invoice_id, "status": "PAID"},
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["status"] == "PAID"

    invoices = client.get(f"/api/project/{project_id}/billing/invoices").json()
    assert len(invoices) == 2
    assert invoices[0]["status"] == "PAID"
    assert invoices[1]["status"] == "PENDING"
    assert invoices[1]["amount"] == 150000


def test_dunning_h3_reminder(client):
    # Clean up any existing invoices/subscriptions from previous tests
    import sqlite3
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM invoices")
        conn.execute("DELETE FROM subscriptions")
        conn.commit()
    finally:
        conn.close()

    project_id = _deployed_project(client)
    assert _project_state(project_id) == "SUBSCRIPTION"

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE invoices SET due_date = ? WHERE project_id = ? AND status = 'PENDING'",
            ((datetime.now(timezone.utc) - timedelta(days=4)).isoformat(), project_id),
        )
        conn.commit()
    finally:
        conn.close()

    actions = client.post("/api/billing/dunning/run").json()
    reminder_actions = [a for a in actions if a["action"] == "REMINDER_SENT"]
    assert len(reminder_actions) == 1
    assert "Wati: Kirim WA Reminder" in reminder_actions[0]["message"]

    state = _project_state(project_id)
    assert state == "SUBSCRIPTION"


def test_dunning_h7_suspend(client):
    # Clean up any existing invoices/subscriptions from previous tests
    import sqlite3
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM invoices")
        conn.execute("DELETE FROM subscriptions")
        conn.commit()
    finally:
        conn.close()

    project_id = _deployed_project(client)
    assert _project_state(project_id) == "SUBSCRIPTION"

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE invoices SET due_date = ? WHERE project_id = ? AND status = 'PENDING'",
            ((datetime.now(timezone.utc) - timedelta(days=8)).isoformat(), project_id),
        )
        conn.commit()
    finally:
        conn.close()

    actions = client.post("/api/billing/dunning/run").json()
    suspend_actions = [a for a in actions if a["action"] == "SUSPENDED"]
    assert len(suspend_actions) == 1
    assert "Om Tono: Suspend website" in suspend_actions[0]["message"]

    state = _project_state(project_id)
    assert state == "SUSPENDED"


def test_dunning_h30_churn(client):
    # Clean up any existing invoices/subscriptions from previous tests
    import sqlite3
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM invoices")
        conn.execute("DELETE FROM subscriptions")
        conn.commit()
    finally:
        conn.close()

    project_id = _deployed_project(client)
    assert _project_state(project_id) == "SUBSCRIPTION"

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE invoices SET due_date = ? WHERE project_id = ? AND status = 'PENDING'",
            ((datetime.now(timezone.utc) - timedelta(days=31)).isoformat(), project_id),
        )
        conn.commit()
    finally:
        conn.close()

    actions = client.post("/api/billing/dunning/run").json()
    churn_actions = [a for a in actions if a["action"] == "CHURNED"]
    assert len(churn_actions) == 1
    assert "Om Tono: Hapus server & DB" in churn_actions[0]["message"]

    state = _project_state(project_id)
    assert state == "CHURNED"


TELEGRAM_WEBHOOK_SECRET = "dev-webhook-secret-change-in-production"
FOUNDER_CHAT_ID = "123456789"
STRANGER_CHAT_ID = "999999999"


def test_security_api_key_required(client):
    client.headers.pop("X-API-Key", None)
    response = client.post("/api/project/start", json={"client_name": "Toko Maju"})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_security_api_key_valid(client):
    response = client.post("/api/project/start", json={"client_name": "Toko Maju"})
    assert response.status_code == 200
    assert response.json()["client_name"] == "Toko Maju"


def test_security_telegram_webhook_secret_required(client):
    response = client.post("/api/telegram/webhook", json={"callback_query": {"data": "APPROVE|test", "from": {"id": FOUNDER_CHAT_ID}}})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_security_telegram_founder_lock_stranger(client, monkeypatch):
    # Create an approval first
    project_id = _approved_project(client)
    deploy_resp = client.post(f"/api/project/{project_id}/deploy/request", json={"domain_choice": "HOSTED"})
    approval_id = deploy_resp.json()["approval_id"]

    # Verify approval is PENDING
    pending = client.get("/api/approvals/pending").json()
    approval = next(a for a in pending if a["approval_id"] == approval_id)
    assert approval["status"] == "PENDING"

    # Stranger tries to approve
    headers = {"X-Telegram-Bot-Api-Secret-Token": TELEGRAM_WEBHOOK_SECRET}
    response = client.post(
        "/api/telegram/webhook",
        json={
            "callback_query": {
                "data": f"APPROVE|{approval_id}",
                "from": {"id": STRANGER_CHAT_ID, "first_name": "Hacker"},
            }
        },
        headers=headers,
    )
    assert response.status_code == 403
    assert "Akses Ditolak" in response.json()["detail"]

    # Verify approval is still PENDING
    pending = client.get("/api/approvals/pending").json()
    approval = next(a for a in pending if a["approval_id"] == approval_id)
    assert approval["status"] == "PENDING"


def test_security_telegram_founder_lock_founder(client, monkeypatch):
    # Create an approval first
    project_id = _approved_project(client)
    deploy_resp = client.post(f"/api/project/{project_id}/deploy/request", json={"domain_choice": "HOSTED"})
    approval_id = deploy_resp.json()["approval_id"]

    # Founder approves
    headers = {"X-Telegram-Bot-Api-Secret-Token": TELEGRAM_WEBHOOK_SECRET}
    response = client.post(
        "/api/telegram/webhook",
        json={
            "callback_query": {
                "data": f"APPROVE|{approval_id}",
                "from": {"id": FOUNDER_CHAT_ID, "first_name": "MUHAMMAD MUFTI ZAKA"},
            }
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    # Verify approval is APPROVED
    pending = client.get("/api/approvals/pending").json()
    approval = next((a for a in pending if a["approval_id"] == approval_id), None)
    assert approval is None or approval["status"] == "APPROVED"

