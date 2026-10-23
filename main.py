import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

import database
from agents.text_quality_gate import score_text
from agents.visual_quality_gate import audit_frontend
from agents.cs_intake import run_discovery
from agents.finance_costing import (
    DiscountHardCap,
    apply_discount,
    calculate_quote,
    estimate_effort,
)
from agents.payment_verification import generate_qris, handle_qris_webhook, VerificationResult
from agents.post_mortem import run_post_mortem
from core.prompt_injector import inject_memory
from core.telegram_bot import send_approval_card, send_access_denied_message
from core.security import verify_api_key, verify_telegram_secret, verify_founder_identity
from core.scheduler import run_scheduler_tick
from database import (
    create_project,
    get_approval,
    get_invoice,
    get_latest_quote,
    get_project,
    get_qris,
    get_qris_by_invoice,
    get_quote,
    init_db,
    list_pending_approvals,
    save_approval,
    save_ledger_entry,
    save_quote,
    update_approval_status,
    update_project_state,
    list_build_tasks,
    list_build_artifacts,
    save_build_task,
    list_audit_reports,
    count_audit_reports,
    get_deployment_by_project,
    list_invoices,
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
    DeploymentRequest,
    DeploymentStatus,
    DiscountRequest,
    DomainChoice,
    FindingSeverity,
    Invoice,
    InvoiceStatus,
    MockLedgerEntry,
    ProjectSpec,
    ProjectState,
    QrisRequest,
    QrisStatus,
    QuoteStatus,
    SignRequest,
    StartProjectRequest,
    Subscription,
    SubscriptionStatus,
    TaskKind,
    TaskStatus,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, dependencies=[Depends(verify_api_key)])


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
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
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
            expires_at=expires_at.isoformat(),
        )
        await save_approval(approval)
        await send_approval_card(approval)
        return JSONResponse(
            status_code=202,
            content={"status": "ESCALATED", "approval_id": approval.approval_id, "expires_at": expires_at.isoformat()},
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

    if approval.type == ApprovalType.DEPLOY_PRODUCTION:
        from agents.technical_ops import execute_deployment
        from agents.billing_dunning import activate_subscription
        from database import get_deployment, save_deployment, update_project_state
        from models import DeploymentStatus

        if decision == "REJECTED":
            await update_approval_status(
                approval_id, ApprovalStatus.REJECTED.value, decided_at, decided_by
            )
            deployment_id = approval.payload.get("deployment_id")
            if deployment_id:
                deployment = await get_deployment(deployment_id)
                if deployment:
                    deployment.status = DeploymentStatus.REJECTED
                    await save_deployment(deployment)
            return {
                "approval_id": approval_id,
                "status": ApprovalStatus.REJECTED.value,
                "deployment_id": deployment_id,
            }

        await update_approval_status(
            approval_id, ApprovalStatus.APPROVED.value, decided_at, decided_by
        )
        result = await execute_deployment(approval_id)

        project_id = approval.payload.get("project_id")
        if project_id:
            await activate_subscription(project_id)

        return {
            "approval_id": approval_id,
            "status": ApprovalStatus.APPROVED.value,
            "deployment": result,
        }

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


@app.post("/api/telegram/webhook", dependencies=[Depends(verify_telegram_secret)])
async def telegram_webhook(payload: dict) -> dict:
    callback = payload.get("callback_query")
    if not isinstance(callback, dict):
        raise HTTPException(status_code=400, detail="callback_query missing")

    data = str(callback.get("data") or "")
    if "|" not in data:
        raise HTTPException(status_code=400, detail="invalid callback data")

    action, approval_id = data.split("|", 1)

    if action not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=400, detail="invalid action")

    decision = "APPROVED" if action == "APPROVE" else "REJECTED"

    sender = callback.get("from") if isinstance(callback.get("from"), dict) else {}
    chat_id = sender.get("id")

    if chat_id is None:
        raise HTTPException(status_code=400, detail="chat_id missing in callback")

    try:
        await verify_founder_identity(chat_id)
    except HTTPException:
        await send_access_denied_message(str(chat_id))
        raise

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


@app.post("/api/project/{project_id}/deploy/request")
async def deploy_request(project_id: str, body: dict) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["state"] != ProjectState.APPROVED.value:
        raise HTTPException(status_code=400, detail="Project must be in APPROVED state")

    domain_choice_str = body.get("domain_choice")
    if domain_choice_str not in ("HOSTED", "CUSTOM"):
        raise HTTPException(status_code=400, detail="domain_choice must be HOSTED or CUSTOM")
    domain_choice = DomainChoice(domain_choice_str)

    custom_domain_url = body.get("custom_domain_url")
    if domain_choice == DomainChoice.CUSTOM and not custom_domain_url:
        raise HTTPException(status_code=400, detail="custom_domain_url required for CUSTOM domain")

    from agents.technical_ops import request_deployment
    try:
        deployment_id, approval_id = await request_deployment(project_id, domain_choice, custom_domain_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "deployment_id": deployment_id,
        "approval_id": approval_id,
        "status": "PENDING_APPROVAL",
    }


@app.post("/api/webhooks/payment/mock")
async def payment_webhook(body: dict) -> dict:
    invoice_id = body.get("invoice_id")
    status = body.get("status")
    if not invoice_id or status != "PAID":
        raise HTTPException(status_code=400, detail="invoice_id and status=PAID required")

    from agents.billing_dunning import process_payment
    try:
        invoice = await process_payment(invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "invoice_id": invoice.invoice_id,
        "status": invoice.status.value,
        "paid_at": invoice.paid_at,
    }


@app.post("/api/billing/dunning/run")
async def run_dunning() -> list[dict]:
    from agents.billing_dunning import run_dunning_sop
    actions = await run_dunning_sop()
    return actions


@app.get("/api/project/{project_id}/billing/invoices")
async def get_project_invoices(project_id: str) -> list[dict]:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    from database import list_invoices
    invoices = await list_invoices(project_id)
    return [inv.model_dump() for inv in invoices]


@app.post("/api/billing/invoices/{invoice_id}/qris")
async def generate_qris_endpoint(invoice_id: str) -> dict:
    invoice = await get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != InvoiceStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invoice is not pending")

    existing_qris = await get_qris_by_invoice(invoice_id)
    if existing_qris and existing_qris.status == QrisStatus.ACTIVE:
        return {
            "qris_id": existing_qris.qris_id,
            "qr_string": existing_qris.qr_string,
            "amount": existing_qris.amount,
            "expires_at": existing_qris.expires_at,
        }

    qris = await generate_qris(invoice)
    return {
        "qris_id": qris.qris_id,
        "qr_string": qris.qr_string,
        "amount": qris.amount,
        "expires_at": qris.expires_at,
    }


@app.get("/api/billing/invoices/{invoice_id}/qris")
async def get_qris_endpoint(invoice_id: str) -> dict:
    invoice = await get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    qris = await get_qris_by_invoice(invoice_id)
    if qris is None:
        raise HTTPException(status_code=404, detail="QRIS not found for this invoice")

    return {
        "qris_id": qris.qris_id,
        "qr_string": qris.qr_string,
        "amount": qris.amount,
        "expires_at": qris.expires_at,
        "status": qris.status.value,
    }


@app.post("/api/mock/qris/simulate_scan")
async def simulate_qris_scan(body: dict) -> dict:
    qris_id = body.get("qris_id")
    paid_amount = body.get("paid_amount")

    if not qris_id or paid_amount is None:
        raise HTTPException(status_code=400, detail="qris_id and paid_amount required")

    qris = await get_qris(qris_id)
    if not qris:
        raise HTTPException(status_code=404, detail="QRIS not found")

    reference_code = f"REF-{uuid.uuid4().hex[:12].upper()}"

    result, message = await handle_qris_webhook(reference_code, qris_id, paid_amount)

    return {
        "verification_result": result.value,
        "message": message,
        "reference_code": reference_code,
    }


@app.post("/api/webhooks/qris", dependencies=[Depends(verify_telegram_secret)])
async def qris_webhook(payload: dict) -> dict:
    reference_code = payload.get("reference_code")
    qris_id = payload.get("qris_id")
    amount = payload.get("amount")

    if not all([reference_code, qris_id, amount is not None]):
        raise HTTPException(status_code=400, detail="reference_code, qris_id, amount required")

    result, message = await handle_qris_webhook(reference_code, qris_id, amount)

    return {
        "verification_result": result.value,
        "message": message,
    }


@app.post("/api/scheduler/tick")
async def scheduler_tick() -> dict:
    return await run_scheduler_tick()


@app.post("/api/project/{project_id}/post-mortem")
async def post_mortem_endpoint(project_id: str) -> dict:
    project = await get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    memories = await run_post_mortem(project_id)
    return {
        "project_id": project_id,
        "memories_created": len(memories),
        "memories": [m.model_dump() for m in memories],
    }


@app.get("/api/memory/inject")
async def memory_inject_endpoint(agent: str) -> dict:
    base_prompt = f"Kamu adalah {agent}"
    injected = await inject_memory(base_prompt, agent.upper())
    return {
        "agent": agent.upper(),
        "base_prompt": base_prompt,
        "injected_prompt": injected,
    }


@app.get("/api/quality/text")
async def text_quality_endpoint(text: str) -> dict:
    return score_text(text)


@app.get("/api/quality/visual")
async def visual_quality_endpoint(artifact_id: str) -> dict:
    from database import get_build_artifact
    artifact = await get_build_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return audit_frontend(artifact.content)


@app.get("/api/prompts/{agent_name}")
async def get_prompt(agent_name: str) -> dict:
    from pathlib import Path
    prompt_path = Path(__file__).resolve().parent / "prompts" / f"{agent_name.lower()}.md"
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail=f"Prompt for agent '{agent_name}' not found")
    content = prompt_path.read_text(encoding="utf-8")
    return {"agent": agent_name, "content": content}

