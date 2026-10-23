import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

from database import (
    get_invoice,
    get_overdue_invoices,
    get_project,
    get_subscription,
    list_invoices,
    save_invoice,
    save_subscription,
    update_project_state,
)
from agents.post_mortem import run_post_mortem
from agents.text_quality_gate import enforce
from models import Invoice, InvoiceStatus, ProjectState, Subscription, SubscriptionStatus


DEFAULT_MONTHLY_FEE = 150_000


def _enforce_text_quality(message: str) -> str:
    """Apply text quality gate to client-facing messages."""
    should_send, msg = enforce(message)
    if should_send:
        return message
    # Log violation and return safe fallback
    return "Halo Bang, info tagihan dari tim kami."


async def activate_subscription(project_id: str, monthly_fee: int = DEFAULT_MONTHLY_FEE) -> Subscription:
    project = await get_project(project_id)
    if project is None:
        raise ValueError("Project not found")
    if project["state"] != ProjectState.DEPLOYED.value:
        raise ValueError("Project must be in DEPLOYED state")

    existing_sub = await get_subscription(project_id)
    if existing_sub:
        return existing_sub

    subscription_id = str(uuid.uuid4())
    invoice_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=30)

    subscription = Subscription(
        subscription_id=subscription_id,
        project_id=project_id,
        monthly_fee=monthly_fee,
        status=SubscriptionStatus.ACTIVE,
        current_invoice_id=invoice_id,
    )
    await save_subscription(subscription)

    invoice = Invoice(
        invoice_id=invoice_id,
        project_id=project_id,
        amount=monthly_fee,
        due_date=due_date.isoformat(),
        status=InvoiceStatus.PENDING,
    )
    await save_invoice(invoice)

    await update_project_state(project_id, ProjectState.SUBSCRIPTION.value)

    await run_post_mortem(project_id)

    return subscription


async def process_payment(invoice_id: str) -> Invoice:
    invoice = await get_invoice(invoice_id)
    if invoice is None:
        raise ValueError("Invoice not found")
    if invoice.status != InvoiceStatus.PENDING:
        raise ValueError("Invoice is not pending")

    now = datetime.now(timezone.utc)
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = now.isoformat()
    await save_invoice(invoice)

    subscription = await get_subscription(invoice.project_id)
    if subscription:
        next_invoice_id = str(uuid.uuid4())
        next_due = now + timedelta(days=30)
        next_invoice = Invoice(
            invoice_id=next_invoice_id,
            project_id=invoice.project_id,
            amount=subscription.monthly_fee,
            due_date=next_due.isoformat(),
            status=InvoiceStatus.PENDING,
        )
        await save_invoice(next_invoice)
        subscription.current_invoice_id = next_invoice_id
        await save_subscription(subscription)

    return invoice


async def run_dunning_sop() -> list[dict]:
    overdue_invoices = await get_overdue_invoices()
    actions = []

    for invoice in overdue_invoices:
        due_dt = datetime.fromisoformat(invoice.due_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_overdue = (now - due_dt).days

        project = await get_project(invoice.project_id)
        if not project:
            continue

        if days_overdue >= 30 and project["state"] != ProjectState.CHURNED.value:
            await update_project_state(invoice.project_id, ProjectState.CHURNED.value)
            invoice.status = InvoiceStatus.CANCELLED
            await save_invoice(invoice)
            subscription = await get_subscription(invoice.project_id)
            if subscription:
                subscription.status = SubscriptionStatus.CHURNED
                await save_subscription(subscription)
            message = _enforce_text_quality("Bang, invoice hosting sudah telat 30 hari. Server kita hapus ya. Kalau mau lanjut, chat kami.")
            actions.append({
                "invoice_id": invoice.invoice_id,
                "project_id": invoice.project_id,
                "days_overdue": days_overdue,
                "action": "CHURNED",
                "message": message,
            })

            await run_post_mortem(invoice.project_id)
        elif days_overdue >= 14 and project["state"] == ProjectState.SUBSCRIPTION.value:
            message = _enforce_text_quality("Bang, tagihan sudah 14 hari lewat. Mau kita tawarin diskon atau downgrade paketnya?")
            actions.append({
                "invoice_id": invoice.invoice_id,
                "project_id": invoice.project_id,
                "days_overdue": days_overdue,
                "action": "RETENTION_OFFER",
                "message": message,
            })
        elif days_overdue >= 7 and project["state"] == ProjectState.SUBSCRIPTION.value:
            await update_project_state(invoice.project_id, ProjectState.SUSPENDED.value)
            subscription = await get_subscription(invoice.project_id)
            if subscription:
                subscription.status = SubscriptionStatus.SUSPENDED
                await save_subscription(subscription)
            message = _enforce_text_quality("Bang, website sudah disuspend karena tagihan telat 7 hari. Bayar dulu baru aktif lagi.")
            actions.append({
                "invoice_id": invoice.invoice_id,
                "project_id": invoice.project_id,
                "days_overdue": days_overdue,
                "action": "SUSPENDED",
                "message": message,
            })
        elif days_overdue >= 3 and project["state"] == ProjectState.SUBSCRIPTION.value:
            message = _enforce_text_quality("Bang, invoice hosting telat 3 hari nih. Ada kendala di pembayaran atau mau saya kirim ulang QRIS-nya?")
            actions.append({
                "invoice_id": invoice.invoice_id,
                "project_id": invoice.project_id,
                "days_overdue": days_overdue,
                "action": "REMINDER_SENT",
                "message": message,
            })

    return actions