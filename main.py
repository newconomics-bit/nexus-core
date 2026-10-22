import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import database
from agents.cs_intake import run_discovery
from agents.finance_costing import (
    DiscountHardCap,
    apply_discount,
    calculate_quote,
    estimate_effort,
)
from core.telegram_gateway import send_approval_request
from database import (
    create_project,
    get_approval,
    get_latest_quote,
    get_project,
    get_quote,
    init_db,
    list_pending_approvals,
    save_approval,
    save_quote,
    update_approval_status,
    update_project_state,
    list_build_tasks,
    list_build_artifacts,
    save_build_task,
    list_audit_reports,
    count_audit_reports,
)
from models import (
    ALLOWED_TRANSITIONS,
    AdvanceStateRequest,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditReportStatus,
    BuildTask,
    ChatRequest,
    DecideRequest,
    DiscountRequest,
    FindingSeverity,
    ProjectSpec,
    ProjectState,
    QuoteStatus,
    SignRequest,
    StartProjectRequest,
    TaskKind,
    TaskStatus,
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
    if body.discount_pct > 30:
        raise HTTPException(status_code=400, detail="DISCOUNT_HARD_CAP")
    if body.discount_pct > 10 and not body.founder_approved:
        projected = apply_discount(quote, body.discount_pct, founder_approved=True)
        approval = ApprovalRequest(
            approval_id=str(uuid.uuid4()),
            project_id=project_id,
            quote_id=quote_id,
            type=ApprovalType.DISCOUNT_ESCALATION,
            payload={
                "discount_pct": body.discount_pct,
                "final_price_before": quote.final_price,
                "final_price_after": projected.final_price,
            },
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        await save_approval(approval)
        await send_approval_request(approval)
        return JSONResponse(
            status_code=202,
            content={"status": "ESCALATED", "approval_id": approval.approval_id},
        )
    try:
        updated = apply_discount(quote, body.discount_pct, body.founder_approved)
    except DiscountHardCap:
        raise HTTPException(status_code=400, detail="DISCOUNT_HARD_CAP") from None
    await save_quote(updated)
    return updated


async def decide_approval(approval_id: str, decision: str, decided_by: str) -> dict:
    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="INVALID_DECISION")
    approval = await get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="APPROVAL_ALREADY_DECIDED")

    decided_at = datetime.now(timezone.utc).isoformat()
    if decision == "REJECTED":
        await update_approval_status(
            approval_id, ApprovalStatus.REJECTED.value, decided_at, decided_by
        )
        quote = await get_quote(approval.quote_id)
        return {
            "approval_id": approval_id,
            "status": ApprovalStatus.REJECTED.value,
            "final_price": None if quote is None else quote.final_price,
            "discount_pct": None if quote is None else quote.discount_pct,
        }

    quote = await get_quote(approval.quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    try:
        updated = apply_discount(
            quote, int(approval.payload["discount_pct"]), founder_approved=True
        )
    except DiscountHardCap:
        raise HTTPException(status_code=400, detail="DISCOUNT_HARD_CAP") from None
    await save_quote(updated)
    await update_approval_status(
        approval_id, ApprovalStatus.APPROVED.value, decided_at, decided_by
    )
    return {
        "approval_id": approval_id,
        "status": ApprovalStatus.APPROVED.value,
        "final_price": updated.final_price,
        "discount_pct": updated.discount_pct,
    }


@app.get("/api/approvals/pending")
async def pending_approvals():
    return await list_pending_approvals()


@app.post("/api/approvals/{approval_id}/decide")
async def decide_approval_endpoint(approval_id: str, body: DecideRequest) -> dict:
    return await decide_approval(approval_id, body.decision, body.decided_by)


@app.post("/api/telegram/webhook")
async def telegram_webhook(payload: dict) -> dict:
    callback = payload.get("callback_query")
    if not isinstance(callback, dict):
        raise HTTPException(status_code=400, detail="callback_query missing")
    data = str(callback.get("data") or "")
    if "|" not in data:
        raise HTTPException(status_code=400, detail="invalid callback data")
    decision, approval_id = data.split("|", 1)
    sender = callback.get("from") if isinstance(callback.get("from"), dict) else {}
    decided_by = sender.get("first_name") or "MUHAMMAD MUFTI ZAKA"
    return await decide_approval(approval_id, decision, decided_by)


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


@app.post("/api/project/{project_id}/build/start")
async def build_start(project_id: str) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["state"] != ProjectState.SIGNED.value:
        raise HTTPException(status_code=400, detail="Project must be in SIGNED state")
    if not project["spec_json"]:
        raise HTTPException(status_code=400, detail="Project spec is missing")

    from agents.engineering_build import breakdown_tasks
    spec = ProjectSpec.model_validate_json(project["spec_json"])
    tasks = breakdown_tasks(spec)
    for task in tasks:
        task.project_id = project_id
        await save_build_task(task)

    await update_project_state(project_id, ProjectState.BUILDING.value)

    return {
        "project_id": project_id,
        "state": ProjectState.BUILDING.value,
        "tasks": [
            {
                "task_id": t.task_id,
                "kind": t.kind.value,
                "title": t.title,
                "status": t.status.value,
            }
            for t in tasks
        ],
    }


@app.post("/api/project/{project_id}/build/run")
async def build_run(project_id: str) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["state"] != ProjectState.BUILDING.value:
        raise HTTPException(status_code=400, detail="Project must be in BUILDING state")

    from agents.engineering_build import run_build
    submission = await run_build(project_id)
    
    if submission.status.startswith("BLOCKED"):
        return {
            "status": "BLOCKED",
            "project_id": project_id,
            "project_state": "BLOCKED",
            "submission": submission.model_dump(),
        }
    
    return {
        "status": submission.status,
        "project_id": project_id,
        "project_state": "AUDITING" if submission.status == "READY_FOR_AUDIT" else project["state"],
        "submission": submission.model_dump(),
    }


@app.get("/api/project/{project_id}/build/status")
async def build_status(project_id: str) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    from agents.engineering_build import get_build_status
    return await get_build_status(project_id)


@app.post("/api/project/{project_id}/audit/run")
async def audit_run(project_id: str) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["state"] != ProjectState.AUDITING.value:
        raise HTTPException(status_code=400, detail="Project must be in AUDITING state")

    from database import get_latest_quote, list_build_submissions
    submissions = await list_build_submissions(project_id)
    if not submissions:
        raise HTTPException(status_code=400, detail="No build submission found")

    latest_submission = submissions[0]

    from agents.qa_audit import run_audit
    report = await run_audit(project_id, latest_submission.submission_id)

    response = report.model_dump()
    if report.status == AuditReportStatus.ESCALATED:
        from database import list_pending_approvals
        pending = await list_pending_approvals()
        qa_escalations = [a for a in pending if a.type == "QA_ESCALATION" and a.project_id == project_id]
        if qa_escalations:
            response["escalation_approval_id"] = qa_escalations[0].approval_id

    return response


@app.get("/api/project/{project_id}/audit/reports")
async def audit_reports(project_id: str) -> list[dict]:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    from database import list_audit_reports
    reports = await list_audit_reports(project_id)
    return [r.model_dump() for r in reports]

