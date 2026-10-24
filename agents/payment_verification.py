import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum

from database import (
    get_expired_qris,
    get_invoice,
    get_ledger_by_reference,
    get_qris,
    get_subscription,
    save_invoice,
    save_ledger_entry,
    save_qris,
    save_subscription,
    insert_audit_log,
)
from agents.proactive_alerts import alert_payment_exception
from models import Invoice, InvoiceStatus, MockLedgerEntry, QrisRequest, QrisStatus, Subscription, AuditAction, AuditResult


async def generate_qris(invoice: Invoice) -> QrisRequest:
    qris_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)
    amount = invoice.amount

    qr_string = f"RAKITDIGITAL|{qris_id}|{amount}|IDR"

    qris = QrisRequest(
        qris_id=qris_id,
        invoice_id=invoice.invoice_id,
        amount=amount,
        qr_string=qr_string,
        status=QrisStatus.ACTIVE,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
    )
    await save_qris(qris)
    return qris


class VerificationResult(str, Enum):
    VERIFIED = "VERIFIED"
    EXCEPTION = "EXCEPTION"
    DUPLICATE = "DUPLICATE"
    INVALID_QRIS = "INVALID_QRIS"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    INVOICE_NOT_PENDING = "INVOICE_NOT_PENDING"


async def handle_qris_webhook(
    reference_code: str,
    qris_id: str,
    amount: int,
) -> tuple[VerificationResult, str]:
    ledger_entry = await get_ledger_by_reference(reference_code)
    if ledger_entry:
        return VerificationResult.DUPLICATE, "Reference code already processed"

    qris = await get_qris(qris_id)
    if not qris or qris.status != QrisStatus.ACTIVE:
        return VerificationResult.INVALID_QRIS, "QRIS not found or not active"

    invoice = await get_invoice(qris.invoice_id)
    if not invoice:
        return VerificationResult.EXCEPTION, "Invoice not found"

    if invoice.status != InvoiceStatus.PENDING:
        return VerificationResult.INVOICE_NOT_PENDING, f"Invoice is {invoice.status.value}, not PENDING"

    if amount != invoice.amount:
        invoice.status = InvoiceStatus.PAYMENT_EXCEPTION
        await save_invoice(invoice)

        # Raise proactive alert
        await alert_payment_exception(
            project_id=invoice.project_id,
            invoice_id=invoice.invoice_id,
            expected=invoice.amount,
            actual=amount,
        )

        return (
            VerificationResult.AMOUNT_MISMATCH,
            f"Amount mismatch: expected {invoice.amount}, got {amount}. Pembayaran kami terima tapi ada selisih/kejanggalan. Tim kami akan follow-up sore ini.",
        )

    now = datetime.now(timezone.utc)

    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = now.isoformat()
    await save_invoice(invoice)

    qris.status = QrisStatus.PAID
    await save_qris(qris)

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

    entry = MockLedgerEntry(
        entry_id=str(uuid.uuid4()),
        reference_code=reference_code,
        qris_id=qris_id,
        amount=amount,
        paid_at=now.isoformat(),
    )
    await save_ledger_entry(entry)

    # Audit log for payment verification
    await insert_audit_log(
        actor="system",
        action=AuditAction.PAYMENT_VERIFIED.value,
        target_id=invoice.invoice_id,
        result=AuditResult.SUCCESS.value,
        context={"reference_code": reference_code, "amount": amount, "qris_id": qris_id},
    )

    return VerificationResult.VERIFIED, "Payment verified successfully"


async def expire_old_qris() -> list[str]:
    expired_qris_list = await get_expired_qris()
    expired_ids = []
    for qris in expired_qris_list:
        qris.status = QrisStatus.EXPIRED
        await save_qris(qris)
        expired_ids.append(qris.qris_id)
    return expired_ids