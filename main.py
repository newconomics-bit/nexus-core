import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import database
from agents.cs_intake import run_discovery
from database import create_project, get_project, init_db, update_project_state
from models import (
    ALLOWED_TRANSITIONS,
    AdvanceStateRequest,
    ChatRequest,
    ProjectState,
    StartProjectRequest,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "brand": "RakitDigital",
        "founder": "MUHAMMAD MUFTI ZAKA",
    }


@app.post("/api/project/start")
async def start_project(body: StartProjectRequest) -> dict:
    project_id = str(uuid.uuid4())
    await create_project(project_id, body.client_name, ProjectState.LEAD.value)
    return {
        "project_id": project_id,
        "client_name": body.client_name,
        "state": ProjectState.LEAD.value,
    }


@app.post("/api/project/{project_id}/advance")
async def advance_project(project_id: str, body: AdvanceStateRequest) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    current = ProjectState(project["state"])
    if body.new_state not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current.value} -> {body.new_state.value}",
        )

    await update_project_state(project_id, body.new_state.value)
    return {"project_id": project_id, "state": body.new_state.value}


@app.post("/api/project/{project_id}/chat")
async def project_chat(project_id: str, body: ChatRequest) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await run_discovery(project_id, body.message, database)
    if result["status"] == "SPEC_COMPLETE":
        await update_project_state(project_id, ProjectState.QUOTED.value)
        result["state"] = ProjectState.QUOTED.value
    return result

