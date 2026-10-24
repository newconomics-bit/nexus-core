import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from database import (
    get_active_client_projects,
    get_onboarding_plan,
    get_support_ticket,
    list_support_tickets,
    save_client_health,
    save_onboarding_plan,
    save_support_ticket,
    update_onboarding_item,
)
from agents.text_quality_gate import enforce
from core.pii_masker import mask_pii_in_text
from models import (
    ClientHealth,
    OnboardingItem,
    OnboardingItemStatus,
    OnboardingPlan,
    SupportTicket,
    TicketStatus,
    TicketCategory,
    OnboardingItemStatus,
)


FAQ_KNOWLEDGE_BASE = {
    "cara input produk": "Untuk input produk: Masuk ke menu Produk > Tambah Produk > Isi nama, harga, stok > Simpan.",
    "cara cetak struk": "Untuk cetak struk: Transaksi selesai > Klik ikon printer di kanan atas > Pilih printer thermal > Cetak.",
    "cara export laporan": "Menu Laporan > Pilih periode > Klik Export Excel/PDF di kanan atas.",
    "cara ganti password": "Profil > Ubah Password > Masukkan password lama & baru > Simpan.",
    "cara tambah user": "Pengguna > Tambah User > Isi nama, email, role > Kirim undangan.",
    "cara backup data": "Pengaturan > Backup Data > Klik Buat Backup > Download file SQL.",
}


DEFAULT_ONBOARDING_ITEMS = [
    {"label": "Login & ganti password", "due_day": 1},
    {"label": "Tonton video training (link mock)", "due_day": 1},
    {"label": "Input 10 data pertama", "due_day": 3},
    {"label": "Transaksi live pertama didampingi", "due_day": 5},
    {"label": "Check-in call dengan Dewi", "due_day": 7},
]


async def generate_onboarding(project_id: str) -> OnboardingPlan:
    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    items = []
    for item_data in DEFAULT_ONBOARDING_ITEMS:
        item = OnboardingItem(
            item_id=str(uuid.uuid4()),
            label=item_data["label"],
            due_day=item_data["due_day"],
            status=OnboardingItemStatus.PENDING,
        )
        items.append(item)
    plan = OnboardingPlan(
        plan_id=plan_id,
        project_id=project_id,
        created_at=now.isoformat(),
        items=items,
    )
    await save_onboarding_plan(plan)
    return plan


async def complete_onboarding_item(project_id: str, item_id: str) -> Optional[OnboardingItem]:
    plan = await get_onboarding_plan(project_id)
    if not plan:
        return None
    for item in plan.items:
        if item.item_id == item_id:
            item.status = OnboardingItemStatus.DONE
            item.completed_at = datetime.now(timezone.utc).isoformat()
            await update_onboarding_item(item_id, OnboardingItemStatus.DONE.value, item.completed_at)
            return item
    return None


async def check_onboarding_progress() -> list[dict]:
    projects = await get_active_client_projects()
    results = []
    for project in projects:
        plan = await get_onboarding_plan(project["id"])
        if not plan:
            continue
        project_created = datetime.fromisoformat(project.get("created_at", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
        days_since_start = (datetime.now(timezone.utc) - project_created).days
        
        # Check for past due items
        for item in plan.items:
            if item.status == OnboardingItemStatus.PENDING and item.due_day <= days_since_start:
                # Send reminder
                message = (
                    f"Halo! Pengingat onboarding: '{item.label}' sudah jatuh tempo "
                    f"(hari ke-{item.due_day}). Yuk diselesaikan ya! Butuh bantuan? Balas pesan ini."
                )
                # Apply text quality gate
                should_send, msg = enforce(message)
                if not should_send:
                    message = "Halo, pengingat onboarding. Ada item yang belum selesai. Butuh bantuan? Balas ya."
                
                # Mock send - print to console
                print(f"MOCK REMINDER to project {project['id']}: {message}")
                
                results.append({
                    "project_id": project["id"],
                    "item_id": item.item_id,
                    "action": "REMINDER_SENT",
                    "message": mask_for_logging(message),
                })

        # Check Day 7 completion rate
        if days_since_start >= 7:
            total = len(plan.items)
            done = sum(1 for i in plan.items if i.status == OnboardingItemStatus.DONE)
            completion_rate = (done / total * 100) if total > 0 else 0
            if completion_rate < 60:
                # Alert Wati (anti-spam: check if already alerted in last 24h)
                # For simplicity, always alert in this implementation
                from agents.proactive_alerts import raise_alert
                from models import AlertType, AlertSeverity
                await raise_alert(
                    alert_type=AlertType.PROJECT_BLOCKED,  # reuse existing type
                    message=f"Onboarding completion {completion_rate:.0f}% (<60%) for project {project['id'][:8]} at Day {days_since_start}. Wati retention needed.",
                    severity=AlertSeverity.WARNING,
                    project_id=project["id"],
                )
                results.append({
                    "project_id": project["id"],
                    "action": "DAY7_LOW_COMPLETION_ALERT",
                    "completion_rate": completion_rate,
                })
    return results


async def triage_ticket(project_id: str, description: str) -> SupportTicket:
    desc_lower = description.lower()
    
    # Determine category
    category = TicketCategory.FAQ
    if any(kw in desc_lower for kw in ["invoice", "bayar", "tagihan", "nominal", "dobel", "payment"]):
        category = TicketCategory.BILLING
    elif any(kw in desc_lower for kw in ["error", "bug", "tidak bisa", "down", "lupa password", "login", "crash", "hang"]):
        category = TicketCategory.TECHNICAL
    
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    if category == TicketCategory.FAQ:
        # Try to find answer in knowledge base - match all keywords in question
        answer = None
        best_match_score = 0
        for question, ans in FAQ_KNOWLEDGE_BASE.items():
            question_keywords = question.split()
            matches = sum(1 for kw in question_keywords if kw in desc_lower)
            if matches > best_match_score:
                best_match_score = matches
                answer = ans
        
        if answer and best_match_score > 0:
            ticket = SupportTicket(
                ticket_id=ticket_id,
                project_id=project_id,
                category=TicketCategory.FAQ,
                description=description,
                status=TicketStatus.RESOLVED,
                auto_answered=True,
                answer=answer,
                created_at=datetime.now(timezone.utc).isoformat(),
                resolved_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            # No match, keep as FAQ but unresolved
            ticket = SupportTicket(
                ticket_id=ticket_id,
                project_id=project_id,
                category=TicketCategory.FAQ,
                description=description,
                status=TicketStatus.OPEN,
                auto_answered=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
    elif category == TicketCategory.TECHNICAL:
        ticket = SupportTicket(
            ticket_id=ticket_id,
            project_id=project_id,
            category=TicketCategory.TECHNICAL,
            description=description,
            status=TicketStatus.ESCALATED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        # Alert Om Tono (technical team)
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.PROJECT_BLOCKED,
            message=f"Technical ticket for project {project_id[:8]}: {description[:100]}. Assigned to Om Tono.",
            severity=AlertSeverity.CRITICAL,
            project_id=project_id,
        )
    else:  # BILLING
        ticket = SupportTicket(
            ticket_id=ticket_id,
            project_id=project_id,
            category=TicketCategory.BILLING,
            description=description,
            status=TicketStatus.ESCALATED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        # Alert Wati (billing team)
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.PAYMENT_EXCEPTION,
            message=f"Billing ticket for project {project_id[:8]}: {description[:100]}. Assigned to Wati.",
            severity=AlertSeverity.WARNING,
            project_id=project_id,
        )
    
    await save_support_ticket(ticket)
    return ticket


async def resolve_ticket(ticket_id: str) -> Optional[SupportTicket]:
    ticket = await get_support_ticket(ticket_id)
    if not ticket:
        return None
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = datetime.now(timezone.utc).isoformat()
    await save_support_ticket(ticket)
    return ticket


def _enforce_text_quality(message: str) -> str:
    should_send, msg = enforce(message)
    if should_send:
        return message
    return "Halo, info dari tim Customer Success kami."


def mask_for_logging(text: str) -> str:
    """Mask PII in text before logging to corporate memory or sending to non-Founder."""
    return mask_pii_in_text(text)


async def compute_health_score(project_id: str) -> ClientHealth:
    from database import get_onboarding_plan, list_invoices, list_support_tickets, get_project
    
    project = await get_project(project_id)
    if not project:
        raise ValueError("Project not found")
    
    plan = await get_onboarding_plan(project_id)
    onboarding_completion = 0.0
    if plan and plan.items:
        done = sum(1 for i in plan.items if i.status == OnboardingItemStatus.DONE)
        onboarding_completion = (done / len(plan.items)) * 100
    
    # Payment history (last 3 invoices)
    invoices = await list_invoices(project_id)
    paid_on_time = 0
    total_recent = 0
    for inv in invoices[:3]:
        if inv.status.value == "PAID" and inv.paid_at and inv.due_date:
            paid_dt = datetime.fromisoformat(inv.paid_at.replace("Z", "+00:00"))
            due_dt = datetime.fromisoformat(inv.due_date.replace("Z", "+00:00"))
            # Ensure both are timezone-aware for comparison
            if paid_dt.tzinfo is None:
                paid_dt = paid_dt.replace(tzinfo=timezone.utc)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            if paid_dt <= due_dt:
                paid_on_time += 1
            total_recent += 1
    payment_score = (paid_on_time / total_recent * 100) if total_recent > 0 else 100
    
    # Open tickets
    open_tickets = await list_support_tickets(project_id=project_id, status="OPEN")
    ticket_penalty = min(len(open_tickets) * 10, 50)  # max 50 penalty
    
    # Last interaction
    last_interaction_days = 30  # mock
    from database import list_support_tickets
    tickets = await list_support_tickets(project_id=project_id)
    if tickets:
        last_ticket = tickets[0]
        last_dt = datetime.fromisoformat(last_ticket.created_at.replace("Z", "+00:00"))
        last_interaction_days = (datetime.now(timezone.utc) - last_dt).days
    interaction_score = max(0, 100 - last_interaction_days * 5)
    
    # Calculate weighted score
    score = int(
        onboarding_completion * 0.4 +
        payment_score * 0.3 +
        max(0, 100 - ticket_penalty) * 0.2 +
        interaction_score * 0.1
    )
    score = max(0, min(100, score))
    
    flagged = score < 50
    
    factors = {
        "onboarding_completion": round(onboarding_completion, 1),
        "payment_score": round(payment_score, 1),
        "ticket_penalty": ticket_penalty,
        "interaction_score": round(interaction_score, 1),
    }
    
    health = ClientHealth(
        project_id=project_id,
        score=score,
        factors=factors,
        flagged=flagged,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
    
    await save_client_health(health)
    
    # Alert if flagged (anti-spam 24h handled by raise_alert)
    if flagged:
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.PROJECT_BLOCKED,
            message=f"Client health score {score} (<50) for project {project_id[:8]}. Factors: {factors}. Wati retention needed.",
            severity=AlertSeverity.WARNING,
            project_id=project_id,
        )
    
    return health


async def check_client_health_all() -> list[ClientHealth]:
    projects = await get_active_client_projects()
    results = []
    for project in projects:
        health = await compute_health_score(project["id"])
        results.append(health)
    return results