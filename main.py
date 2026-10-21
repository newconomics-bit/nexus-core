import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import database
from agents.cs_intake import run_discovery
from agents.finance_costing import (
    DiscountHardCap,
    EscalationRequired,
    apply_discount,
    calculate_quote,
    estimate_effort,
)
from database import (
    create_project,
    get_latest_quote,
    get_project,
    get_quote,
    init_db,
    save_quote,
    update_project_state,
)
from models import (
    ALLOWED_TRANSITIONS,
    AdvanceStateRequest,
    ChatRequest,
    DiscountRequest,
    ProjectSpec,
    ProjectState,
    QuoteStatus,
    SignRequest,
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


@app.post("/api/project/{project_id}/quote/generate")
async def generate_project_quote(project_id: str):
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["state"] != ProjectState.QUOTED.value:
        raise HTTPException(status_code=400, detail="Project state must be QUOTED")
    if not project["spec_json"]:
        raise HTTPException(status_code=400, detail="Project spec is missing")

    spec = ProjectSpec.model_validate_json(project["spec_json"])
    quote = await calculate_quote(project_id, spec, estimate_effort(spec))
    latest = await get_latest_quote(project_id)
    if latest is not None and latest.status == QuoteStatus.ACTIVE:
        await save_quote(latest.model_copy(update={"status": QuoteStatus.EXPIRED}))
    await save_quote(quote)
    return quote


@app.post("/api/project/{project_id}/quote/{quote_id}/discount")
async def discount_quote(project_id: str, quote_id: str, body: DiscountRequest):
    quote = await get_quote(quote_id)
    if quote is None or quote.project_id != project_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    try:
        updated = apply_discount(quote, body.discount_pct, body.founder_approved)
    except DiscountHardCap:
        raise HTTPException(status_code=400, detail="DISCOUNT_HARD_CAP") from None
    except EscalationRequired:
        raise HTTPException(status_code=409, detail="ESCALATION_REQUIRED") from None
    await save_quote(updated)
    return updated


@app.post("/api/project/{project_id}/sign")
async def sign_project(project_id: str, body: SignRequest) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    quote = await get_quote(body.quote_id)
    if quote is None or quote.project_id != project_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    latest = await get_latest_quote(project_id)
    if (
        latest is None
        or quote.quote_id != latest.quote_id
        or quote.version != latest.version
        or quote.status != QuoteStatus.ACTIVE
    ):
        raise HTTPException(status_code=400, detail="QUOTE_NOT_LATEST_OR_INACTIVE")

    accepted = quote.model_copy(update={"status": QuoteStatus.ACCEPTED})
    await save_quote(accepted)
    await update_project_state(project_id, ProjectState.SIGNED.value)
    return {
        "project_id": project_id,
        "quote_id": accepted.quote_id,
        "state": ProjectState.SIGNED.value,
        "quote_status": accepted.status.value,
    }

