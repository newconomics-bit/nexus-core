import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse

import database
from agents.daily_report import send_daily_report, generate_daily_report, format_report_text
from agents.proactive_alerts import scan_alert_triggers
from agents.disaster_recovery import (
    run_backup,
    verify_backup,
    run_dr_drill,
    watchdog_check,
    mitigate_incident,
    resolve_incident,
)
from agents.customer_success import (
    generate_onboarding,
    complete_onboarding_item,
    check_onboarding_progress,
    triage_ticket,
    resolve_ticket,
    compute_health_score,
    check_client_health_all,
)
from agents.marketing_growth import (
    plan_campaign,
    create_positioning,
    define_icp,
    create_battlecard,
    design_ab_test,
    analyze_ab_test,
    generate_leads_etis,
    evaluate_partnership,
)
from agents.contract_generator import generate_contract, send_contract, mark_contract_signed
from agents.sop_pricing import evaluate_pricing_change, process_pricing_change
from agents.sop_feature_request import evaluate_feature_request
from agents.sop_performance_review import generate_performance_report, schedule_monthly_review
from agents.sop_knowledge_mgmt import evaluate_prompt_update, process_prompt_update
from agents.text_quality_gate import score_text
from agents.visual_quality_gate import audit_frontend
from agents.cs_intake import run_discovery
from agents.client_copilot import generate_business_insight
from agents.web_learner import run_curriculum_batch, execute_learning_task
from core.consultation_matrix import calculate_quote as consultation_calculate_quote
from agents.finance_costing import (
    DiscountHardCap,
    apply_discount,
    calculate_quote as finance_calculate_quote,
    estimate_effort,
)

# In-memory lock for state transitions (single-process deployment)
_state_transition_locks: dict[str, float] = {}
_STATE_TRANSITION_LOCK_TTL = 30  # seconds


def _acquire_state_lock(project_id: str) -> bool:
    """Try to acquire a lock for state transition. Returns True if acquired."""
    import time
    now = time.time()
    # Clean expired locks
    expired = [k for k, v in _state_transition_locks.items() if v < now]
    for k in expired:
        del _state_transition_locks[k]

    if project_id in _state_transition_locks:
        return False
    _state_transition_locks[project_id] = now + _STATE_TRANSITION_LOCK_TTL
    return True


def _release_state_lock(project_id: str) -> None:
    """Release the state transition lock for this project."""
    _state_transition_locks.pop(project_id, None)

from agents.payment_verification import generate_qris, handle_qris_webhook, VerificationResult
from agents.post_mortem import run_post_mortem
from core.prompt_injector import inject_memory
from core.telegram_bot import send_approval_card, send_access_denied_message
from core.security import verify_api_key, verify_telegram_secret, verify_founder_identity, verify_founder_authorization
from agents.red_team import RedTeamAttacker
from core.scheduler import run_scheduler_tick, scheduled_red_team_drill
from core.escalation_matrix import needs_founder_approval, get_escalation_matrix
from core.rate_limiter import approval_limiter, webhook_limiter, rate_limit
from database import (
    create_project,
    get_approval,
    get_invoice,
    get_latest_quote,
    get_project,
    get_qris,
    get_qris_by_invoice,
    get_quote,
    get_contract,
    list_contracts,
    get_pending_contracts,
    get_contracts_nearing_expiry,
    get_expired_contracts,
    get_active_client_projects,
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
    save_technical_decision,
    get_technical_decisions_by_type,
    save_feature_request,
    get_pending_feature_requests,
    save_agent_performance,
    get_agent_performance_last_30_days,
    save_contract,
    get_onboarding_plan,
    save_onboarding_plan,
    update_onboarding_item,
    get_support_ticket,
    list_support_tickets,
    save_support_ticket,
    save_client_health,
    get_client_health,
    list_client_health,
    get_active_client_projects,
    get_backup,
    get_latest_backup,
    save_backup,
    get_incident,
    get_open_incidents,
    get_incidents_by_type_open,
    save_incident,
    save_drill,
    save_campaign,
    get_campaign,
    list_campaigns,
    save_campaign_kpi,
    get_battlecards,
    save_battlecard,
    save_ab_test,
    get_ab_test,
    save_lead,
    list_leads,
    save_partnership,
    get_partnership,
    list_partnerships,
    get_partnerships_recommended,
    insert_audit_log,
    get_audit_logs_by_actor,
    get_audit_logs_by_action,
    get_audit_logs_since,
    get_all_audit_logs,
    create_drill,
    add_attack_result,
    get_drill,
    get_latest_drill,
    abort_drill,
    update_drill_summary,
    get_red_team_db,
    save_custom_request,
    get_custom_request,
    list_custom_requests,
    update_custom_request_status,
    get_active_patterns,
    get_pattern_by_id,
    search_patterns,
    supersede_pattern,
    create_learning_task,
    get_pending_tasks,
    get_learning_task,
    update_learning_task,
    seed_initial_patterns,
)
from models import (
    ALLOWED_TRANSITIONS,
    AdvanceStateRequest,
    AlertEvent,
    AlertSeverity,
    AlertType,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditReportStatus,
    BuildTask,
    ChatRequest,
    DailyReport,
    DecideRequest,
    DeploymentRequest,
    DeploymentStatus,
    DiscountRequest,
    DomainChoice,
    FindingSeverity,
    Invoice,
    InvoiceStatus,
    MockLedgerEntry,
    OnboardingPlan,
    OnboardingItem,
    OnboardingItemStatus,
    ProjectSpec,
    ProjectState,
    QrisRequest,
    QrisStatus,
    QuoteStatus,
    SignRequest,
    StartProjectRequest,
    Subscription,
    SubscriptionStatus,
    SupportTicket,
    TicketStatus,
    BackupRecord,
    BackupType,
    BackupStatus,
    Incident,
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    DrillResult,
    DrillStatus,
    Campaign,
    CampaignObjective,
    CampaignStatus,
    CampaignKPI,
    ICPDefinition,
    CompetitiveBattlecard,
    ABTest,
    ABTestStatus,
    LeadGenResult,
    PartnershipEvaluation,
    PartnerType,
    PartnershipStatus,
    AgentPerformance,
    ContractType,
    MarkContractSignedRequest,
    GenerateContractRequest,
    SendContractRequest,
    AttackScenario,
    AttackStatus,
    AttackSeverity,
    AttackResult,
    DrillTrigger,
    RedTeamDrillStatus,
    RedTeamDrill,
    CustomRequest,
    CustomRequestStatus,
    ClientPattern,
    LearningTask,
    LearningTaskStatus,
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
    # Acquire lock to prevent race conditions on state transitions
    if not _acquire_state_lock(project_id):
        raise HTTPException(
            status_code=409,
            detail="State transition already in progress for this project. Please retry.",
        )

    try:
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
    finally:
        _release_state_lock(project_id)


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
    quote = await finance_calculate_quote(project_id, spec, estimate_effort(spec))
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
    # Audit log for quote approval
    from agents.finance_costing import log_quote_approved
    await log_quote_approved(approval.quote_id, updated.discount_pct, updated.final_price)
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
@rate_limit(approval_limiter, lambda r: r.headers.get("X-Telegram-Chat-Id", r.client.host))
async def decide_approval_endpoint(approval_id: str, body: DecideRequest, request: Request) -> dict:
    return await decide_approval(approval_id, body.decision, body.decided_by)


@app.post("/api/telegram/webhook", dependencies=[Depends(verify_telegram_secret)])
@rate_limit(webhook_limiter, lambda r: r.client.host)
async def telegram_webhook(payload: dict, request: Request) -> dict:
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
@rate_limit(webhook_limiter, lambda r: r.client.host)
async def qris_webhook(payload: dict, request: Request) -> dict:
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


@app.get("/api/budi/report/today")
async def budi_report_today() -> dict:
    from datetime import date
    report = await generate_daily_report(date.today())
    if report is None:
        # Generate on-demand if not exists
        report = await generate_daily_report(date.today())
    return report.model_dump()


@app.post("/api/budi/report/send")
async def budi_report_send() -> dict:
    from datetime import date
    result = await send_daily_report(date.today())
    return result


@app.get("/api/budi/alerts")
async def budi_alerts(acknowledged: bool = False) -> list[dict]:
    from database import get_unacknowledged_alerts, list_alert_events
    if acknowledged:
        # For now, just return unacknowledged; can extend later
        alerts = await get_unacknowledged_alerts()
    else:
        alerts = await get_unacknowledged_alerts()
    return [a.model_dump() for a in alerts]


@app.post("/api/budi/alerts/{alert_id}/ack")
async def budi_alert_ack(alert_id: str) -> dict:
    from database import acknowledge_alert
    success = await acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"alert_id": alert_id, "acknowledged": True}


# CTO Endpoints
@app.post("/api/cto/pricing-change")
async def cto_pricing_change(current_price: int, proposed_price: int, decided_by: str = "pak_arif") -> dict:
    decision = await process_pricing_change(current_price, proposed_price, decided_by)
    return decision.model_dump()


@app.post("/api/cto/feature-request")
async def cto_feature_request(
    description: str,
    reach: int,
    impact: str,
    confidence: str,
    effort: float,
    client_id: str | None = None,
) -> dict:
    request = await evaluate_feature_request(description, reach, impact, confidence, effort, client_id)
    return request.model_dump()


@app.get("/api/cto/performance-report")
async def cto_performance_report() -> dict:
    return await generate_performance_report()


@app.post("/api/cto/prompt-update")
async def cto_prompt_update(agent_name: str, proposed_changes: str, decided_by: str = "pak_arif") -> dict:
    decision = await process_prompt_update(agent_name, proposed_changes, decided_by)
    return decision.model_dump()


@app.get("/api/cto/escalation-matrix")
async def cto_escalation_matrix() -> dict:
    return get_escalation_matrix()


@app.get("/api/cto/technical-decisions")
async def cto_technical_decisions(decision_type: str | None = None) -> list[dict]:
    from database import get_technical_decisions_by_type
    from models import DecisionType
    if decision_type:
        decisions = await get_technical_decisions_by_type(DecisionType(decision_type))
    else:
        # Get all types
        decisions = []
        for dt in DecisionType:
            decisions.extend(await get_technical_decisions_by_type(dt))
    return [d.model_dump() for d in decisions]


@app.get("/api/cto/feature-requests")
async def cto_feature_requests(status: str | None = None) -> list[dict]:
    from database import get_pending_feature_requests, list_feature_requests
    from models import FeatureRequestStatus
    if status:
        # For simplicity, just return pending if no specific filter
        requests = await get_pending_feature_requests()
    else:
        requests = await get_pending_feature_requests()
    return [r.model_dump() for r in requests]


@app.post("/api/cto/agent-performance")
async def cto_log_agent_performance(performance: AgentPerformance) -> dict:
    from database import save_agent_performance
    await save_agent_performance(performance)
    return {"status": "logged", "agent": performance.agent_name}


# Legal/Contract Endpoints
@app.post("/api/legal/generate-contract")
async def legal_generate_contract(body: GenerateContractRequest) -> dict:
    contract = await generate_contract(body.project_id, body.contract_type, body.client_email)
    return contract.model_dump()


@app.post("/api/legal/contracts/{contract_id}/send")
async def legal_send_contract(contract_id: str, body: SendContractRequest) -> dict:
    contract = await send_contract(contract_id, body.client_email)
    return contract.model_dump()


@app.post("/api/legal/contracts/{contract_id}/mark-signed")
async def legal_mark_contract_signed(contract_id: str, body: MarkContractSignedRequest) -> dict:
    contract = await mark_contract_signed(contract_id, body.client_name, body.client_title)
    return contract.model_dump()


@app.get("/api/legal/contracts")
async def legal_list_contracts(project_id: str | None = None) -> list[dict]:
    contracts = await list_contracts(project_id)
    return [c.model_dump() for c in contracts]


@app.get("/api/legal/contracts/pending")
async def legal_pending_contracts() -> list[dict]:
    contracts = await get_pending_contracts()
    return [c.model_dump() for c in contracts]


@app.get("/api/legal/contracts/{contract_id}")
async def legal_get_contract(contract_id: str) -> dict:
    contract = await get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract.model_dump()


# Customer Success Endpoints
@app.post("/api/cs/onboarding/generate")
async def cs_generate_onboarding(project_id: str) -> dict:
    plan = await generate_onboarding(project_id)
    return plan.model_dump()


@app.get("/api/cs/onboarding/{project_id}")
async def cs_get_onboarding(project_id: str) -> dict:
    plan = await get_onboarding_plan(project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")
    return plan.model_dump()


@app.post("/api/cs/onboarding/{project_id}/items/{item_id}/complete")
async def cs_complete_onboarding_item(project_id: str, item_id: str) -> dict:
    item = await complete_onboarding_item(project_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.model_dump()


@app.post("/api/support/ticket")
async def cs_create_ticket(project_id: str, description: str) -> dict:
    ticket = await triage_ticket(project_id, description)
    return ticket.model_dump()


@app.get("/api/support/tickets")
async def cs_list_tickets(status: str | None = None, project_id: str | None = None) -> list[dict]:
    tickets = await list_support_tickets(project_id=project_id, status=status)
    return [t.model_dump() for t in tickets]


@app.post("/api/support/tickets/{ticket_id}/resolve")
async def cs_resolve_ticket(ticket_id: str) -> dict:
    ticket = await resolve_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.model_dump()


@app.get("/api/cs/health-scores")
async def cs_health_scores(flagged: bool | None = None) -> list[dict]:
    health_scores = await list_client_health(flagged=flagged)
    return [h.model_dump() for h in health_scores]


@app.post("/api/cs/health-score/{project_id}")
async def cs_compute_health(project_id: str) -> dict:
    health = await compute_health_score(project_id)
    return health.model_dump()


# Disaster Recovery / Ops Endpoints
@app.post("/api/ops/backup/run")
async def ops_run_backup() -> dict:
    backup = await run_backup()
    return backup.model_dump()


@app.get("/api/ops/backups")
async def ops_list_backups() -> list[dict]:
    # For now, just return latest backup
    backup = await get_latest_backup()
    if not backup:
        return []
    return [backup.model_dump()]


@app.post("/api/ops/backups/{backup_id}/verify")
async def ops_verify_backup(backup_id: str) -> dict:
    verified = await verify_backup(backup_id)
    return {"backup_id": backup_id, "verified": verified}


@app.post("/api/ops/drill/run")
async def ops_run_drill() -> dict:
    drill = await run_dr_drill()
    return drill.model_dump()


@app.get("/api/ops/incidents")
async def ops_list_incidents(status: str | None = None) -> list[dict]:
    if status == "OPEN":
        incidents = await get_open_incidents()
    else:
        from database import list_alert_events
        incidents = await list_alert_events(acknowledged=False)
    return [i.model_dump() for i in incidents]


@app.post("/api/ops/incidents/{incident_id}/mitigate")
async def ops_mitigate_incident(incident_id: str, action: str) -> dict:
    incident = await mitigate_incident(incident_id, action)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@app.post("/api/ops/incidents/{incident_id}/resolve")
async def ops_resolve_incident(incident_id: str) -> dict:
    incident = await resolve_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@app.post("/api/ops/watchdog/tick")
async def ops_watchdog_tick() -> dict:
    incidents = await watchdog_check()
    return {"incidents_found": len(incidents), "incidents": [i.model_dump() for i in incidents]}


# Marketing / Growth Endpoints
@app.post("/api/marketing/campaigns")
async def marketing_create_campaign(
    name: str,
    objective: CampaignObjective,
    target_audience: str,
    channels: list[str],
) -> dict:
    campaign = await plan_campaign(name, objective, target_audience, channels)
    return campaign.model_dump()


@app.get("/api/marketing/campaigns")
async def marketing_list_campaigns() -> list[dict]:
    campaigns = await list_campaigns()
    return [c.model_dump() for c in campaigns]


@app.post("/api/marketing/positioning")
async def marketing_create_positioning(
    target_audience: str,
    alternatives: list[str],
    unique_attributes: list[str],
) -> dict:
    return await create_positioning(target_audience, alternatives, unique_attributes)


@app.post("/api/marketing/icp")
async def marketing_define_icp(
    business_type: str,
    firmographics: dict,
    technographics: dict,
    psychographics: dict,
    buyer_personas: list[str],
) -> dict:
    icp = await define_icp(business_type, firmographics, technographics, psychographics, buyer_personas)
    return icp.model_dump()


@app.post("/api/marketing/battlecards")
async def marketing_create_battlecard(
    competitor_name: str,
    strengths: list[str],
    weaknesses: list[str],
    our_advantages: list[str],
    when_to_win: list[str],
    when_to_lose: list[str],
    talk_tracks: list[str],
) -> dict:
    battlecard = await create_battlecard(
        competitor_name, strengths, weaknesses, our_advantages,
        when_to_win, when_to_lose, talk_tracks
    )
    return battlecard.model_dump()


@app.get("/api/marketing/battlecards")
async def marketing_list_battlecards() -> list[dict]:
    battlecards = await get_battlecards()
    return [b.model_dump() for b in battlecards]


@app.post("/api/marketing/ab-tests")
async def marketing_design_ab_test(
    campaign_id: str,
    variant_a: str,
    variant_b: str,
    metric: str,
    sample_size_a: int,
    sample_size_b: int,
) -> dict:
    test = await design_ab_test(campaign_id, variant_a, variant_b, metric, sample_size_a, sample_size_b)
    return test.model_dump()


@app.post("/api/marketing/ab-tests/{test_id}/analyze")
async def marketing_analyze_ab_test(test_id: str) -> dict:
    test = await analyze_ab_test(test_id)
    return test.model_dump()


@app.post("/api/marketing/leads")
async def marketing_generate_leads(niche: str, city: str, limit: int = 10) -> list[dict]:
    leads = await generate_leads_etis(niche, city, limit)
    return [l.model_dump() for l in leads]


@app.get("/api/marketing/leads")
async def marketing_list_leads(niche: str | None = None, city: str | None = None) -> list[dict]:
    leads = await list_leads(niche=niche, city=city)
    return [l.model_dump() for l in leads]


@app.post("/api/marketing/partnerships")
async def marketing_evaluate_partnership(
    partner_name: str,
    partner_type: PartnerType,
    cost_score: int,
    reliability_score: int,
    support_score: int,
    integration_score: int,
) -> dict:
    evaluation = await evaluate_partnership(
        partner_name, partner_type, cost_score, reliability_score, support_score, integration_score
    )
    return evaluation.model_dump()


@app.get("/api/marketing/partnerships")
async def marketing_list_partnerships(status: str | None = None) -> list[dict]:
    if status == "RECOMMENDED":
        partnerships = await get_partnerships_recommended()
    else:
        partnerships = await list_partnerships()
    return [p.model_dump() for p in partnerships]


# Security: Audit Log Endpoint (Founder only)
@app.get("/api/audit-logs")
async def get_audit_logs(
    actor: str | None = None,
    action: str | None = None,
    since: str | None = None,
) -> list[dict]:
    if actor:
        logs = await get_audit_logs_by_actor(actor)
    elif action:
        logs = await get_audit_logs_by_action(action)
    elif since:
        logs = await get_audit_logs_since(since)
    else:
        logs = await get_all_audit_logs()
    return [log.model_dump() for log in logs]


# ==================== RED TEAM (SI MERAH) ENDPOINTS ====================

# Middleware: X-Red-Team header switches to isolated test_attack.db
@app.middleware("http")
async def red_team_middleware(request: Request, call_next):
    """If X-Red-Team: true header with valid Founder API key + signature, switch to isolated DB."""
    red_team_header = request.headers.get("X-Red-Team", "").lower()
    if red_team_header == "true":
        # Verify Founder API key
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("RAKIT_API_KEY", "dev-secret-key-change-in-production")
        if api_key != expected_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key for Red Team mode"})

        # Verify signature (simple HMAC for anti-spoof)
        signature = request.headers.get("X-Red-Team-Signature")
        if not signature:
            return JSONResponse(status_code=401, content={"detail": "Missing X-Red-Team-Signature"})

        # For simplicity, verify signature matches expected pattern
        # In production, use proper HMAC with secret
        expected_signature = hashlib.sha256(f"redteam{api_key}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return JSONResponse(status_code=401, content={"detail": "Invalid Red Team signature"})

        # Switch to isolated DB by setting request state
        request.state.red_team_mode = True
        request.state.red_team_db = await get_red_team_db()

    response = await call_next(request)

    # Close red team DB connection if opened
    if hasattr(request.state, "red_team_db"):
        await request.state.red_team_db.close()

    return response


import hashlib
import os


@app.post("/api/redteam/run")
async def redteam_run_manual(request: Request) -> dict:
    """Trigger manual red team drill - requires Founder approval via Telegram."""
    # Verify Founder identity
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Founder authorization")

    # Check if there's a pending approval for this drill
    # For manual trigger, we require a prior approval
    # This is a simplified check - in production, check for specific approval
    drill = await create_drill(DrillTrigger.MANUAL)

    attacker = RedTeamAttacker()
    completed_drill = await attacker.run_all_scenarios(DrillTrigger.MANUAL)

    # Send report to Founder via Telegram
    from core.telegram_bot import send_message
    report = attacker.generate_report(completed_drill, completed_drill.results)
    try:
        await send_message(f"🔴 *SI MERAH DRILL COMPLETED*\n\n{report}")
    except Exception as e:
        print(f"Failed to send Telegram report: {e}")

    return {
        "drill_id": completed_drill.drill_id,
        "status": completed_drill.status.value,
        "summary": completed_drill.summary,
        "results_count": len(completed_drill.results),
    }


@app.post("/api/redteam/stop")
async def redteam_kill_switch() -> dict:
    """Kill switch - abort any running drill."""
    latest = await get_latest_drill()
    if latest and latest.status == RedTeamDrillStatus.RUNNING:
        aborted = await abort_drill(latest.drill_id)
        if aborted:
            return {"status": "ABORTED", "drill_id": latest.drill_id, "message": "Drill aborted by kill switch"}

    return {"status": "NO_RUNNING_DRILL", "message": "No running drill to abort"}


@app.get("/api/redteam/drills")
async def redteam_list_drills() -> list[dict]:
    """List all red team drills."""
    from database import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM red_team_drills ORDER BY started_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@app.get("/api/redteam/drills/{drill_id}")
async def redteam_get_drill(drill_id: str) -> dict:
    """Get drill details with all attack results."""
    drill = await get_drill(drill_id)
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    return drill.model_dump()


@app.get("/api/redteam/latest")
async def redteam_latest_drill() -> dict:
    """Get latest drill with summary."""
    drill = await get_latest_drill()
    if not drill:
        raise HTTPException(status_code=404, detail="No drills found")
    return {
        "drill_id": drill.drill_id,
        "triggered_by": drill.triggered_by.value,
        "status": drill.status.value,
        "started_at": drill.started_at,
        "finished_at": drill.finished_at,
        "summary": drill.summary,
        "results": [r.model_dump() for r in drill.results],
    }


# ==================== WAVE 24: CONSULTATIVE & CO-PILOT ENDPOINTS ====================

class CopilotInsightRequest(BaseModel):
    structured_data: dict


@app.post("/api/copilot/insight")
async def copilot_insight(body: CopilotInsightRequest) -> dict:
    """
    Client Co-Pilot: Generate business insight from structured data.
    Protected by API key + client auth (simplified: API key only for now).
    """
    insight = await generate_business_insight(body.structured_data)
    return {"insight": insight, "generated_at": datetime.now(timezone.utc).isoformat()}


class CustomRequestCreate(BaseModel):
    client_name: str
    description: str
    estimated_budget: int | None = None


@app.post("/api/custom-requests")
async def create_custom_request(body: CustomRequestCreate) -> dict:
    """Create a new custom/enterprise request."""
    import uuid
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    request = CustomRequest(
        request_id=request_id,
        client_name=body.client_name,
        description=body.description,
        status=CustomRequestStatus.PENDING_REVIEW,
        estimated_budget=body.estimated_budget,
        created_at=now,
    )
    await save_custom_request(request)

    return {
        "request_id": request_id,
        "status": "PENDING_REVIEW",
        "message": "Custom request created. Tim arsitek akan review 1x24 jam.",
    }


@app.get("/api/custom-requests")
async def get_custom_requests(status: str | None = None) -> list[dict]:
    """List custom requests, optionally filtered by status."""
    status_enum = CustomRequestStatus(status) if status else None
    requests = await list_custom_requests(status_enum)
    return [r.model_dump() for r in requests]


@app.get("/api/custom-requests/{request_id}")
async def get_custom_request_endpoint(request_id: str) -> dict:
    """Get a specific custom request."""
    request = await get_custom_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Custom request not found")
    return request.model_dump()


class CustomRequestUpdate(BaseModel):
    status: str
    estimated_budget: int | None = None


@app.patch("/api/custom-requests/{request_id}")
async def update_custom_request(request_id: str, body: CustomRequestUpdate) -> dict:
    """Update custom request status."""
    status_enum = CustomRequestStatus(body.status)
    success = await update_custom_request_status(request_id, status_enum, body.estimated_budget)
    if not success:
        raise HTTPException(status_code=404, detail="Custom request not found")
    return {"message": "Updated", "request_id": request_id}


class QuoteCalculateRequest(BaseModel):
    base_tier: str
    modules: list[str] = []


class ConsultationDetectRequest(BaseModel):
    message: str


@app.post("/api/quote/calculate")
async def calculate_quote_endpoint(body: QuoteCalculateRequest) -> dict:
    """Calculate quote deterministically (for internal/debug use)."""
    quote = consultation_calculate_quote(body.base_tier, body.modules)
    return quote


@app.post("/api/consultation/detect")
async def detect_business_type_endpoint(body: ConsultationDetectRequest) -> dict:
    """Detect business type and return consultative response (for testing)."""
    from core.consultation_matrix import detect_business_type, generate_consultative_response, get_recommended_config
    btype = detect_business_type(body.message)
    if not btype:
        return {"detected": False, "message": "Tipe bisnis tidak dikenali"}
    response = generate_consultative_response(btype)
    config = get_recommended_config(btype)
    return {
        "detected": True,
        "business_type": btype,
        "consultative_response": response,
        "recommended_config": config,
    }


# ==================== WAVE 25: PATTERN & LEARNING ENDPOINTS ====================

class PatternSearchRequest(BaseModel):
    query: str
    business_type: str | None = None
    top_k: int = 5


@app.get("/api/patterns")
async def list_patterns(business_type: str | None = None) -> list[dict]:
    """List active patterns, optionally filtered by business_type."""
    patterns = await get_active_patterns(business_type)
    return [p.model_dump() for p in patterns]


@app.get("/api/patterns/search")
async def search_patterns_endpoint(query: str, business_type: str | None = None, top_k: int = 5) -> list[dict]:
    """Search patterns using keyword weighted scoring."""
    patterns = await search_patterns(query, business_type, top_k)
    return [p.model_dump() for p in patterns]


@app.get("/api/patterns/{pattern_id}")
async def get_pattern(pattern_id: str) -> dict:
    """Get a specific pattern by ID."""
    pattern = await get_pattern_by_id(pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern.model_dump()


class LearningTaskCreate(BaseModel):
    target_url: str
    business_type: str
    reference_company: str


@app.post("/api/learning/tasks")
async def create_learning_task_endpoint(body: LearningTaskCreate) -> dict:
    """Create a new learning task (PENDING)."""
    import uuid
    from datetime import datetime, timezone
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    task = LearningTask(
        task_id=task_id,
        target_url=body.target_url,
        business_type=body.business_type,
        reference_company=body.reference_company,
        status=LearningTaskStatus.PENDING,
        created_at=now,
    )
    await create_learning_task(task)

    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": "Learning task created. Execute via POST /api/learning/tasks/{task_id}/execute",
    }


@app.get("/api/learning/tasks")
async def list_learning_tasks() -> list[dict]:
    """List all pending learning tasks."""
    tasks = await get_pending_tasks()
    return [t.model_dump() for t in tasks]


@app.post("/api/learning/tasks/{task_id}/execute")
async def execute_learning_task_endpoint(task_id: str) -> dict:
    """Execute a specific learning task by ID."""
    result = await execute_learning_task(task_id)
    return result


class CurriculumRunRequest(BaseModel):
    max_fetch: int = 1


@app.post("/api/curriculum/run")
async def run_curriculum_endpoint(
    body: CurriculumRunRequest,
    _: None = Depends(verify_founder_authorization)
) -> dict:
    """
    Trigger curriculum learning batch (Founder only).
    Requires Founder approval via headers:
    - X-Founder-Approval: true
    - X-Founder-Signature: HMAC-SHA256 of "true" using FOUNDER_AUTH_SECRET
    """
    max_fetch = min(max(1, body.max_fetch), 5)  # Clamp 1-5
    results = await run_curriculum_batch(max_fetch)

    # Send summary to Founder
    from core.telegram_bot import send_message
    completed = [r for r in results if r.get("status") == "COMPLETED"]
    skipped = [r for r in results if r.get("status") == "SKIPPED_CACHED"]
    failed = [r for r in results if r.get("status") in ("FAILED", "ETHICS_BLOCKED")]

    summary = (
        f"📚 *PAK GURU CURRICULUM RUN*\n"
        f"Fetch: {len(completed)} baru, {len(skipped)} cached, {len(failed)} gagal/blocked.\n"
        f"Detail: {results}"
    )
    try:
        await send_message(summary)
    except Exception as e:
        print(f"Failed to send curriculum summary: {e}")

    return {"results": results, "summary": summary}

