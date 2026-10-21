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

