from datetime import datetime, timezone
from database import (
    get_expired_approvals,
    update_approval_status,
    get_contracts_nearing_expiry,
    get_expired_contracts,
)
from agents.payment_verification import expire_old_qris
from agents.daily_report import send_daily_report
from agents.proactive_alerts import scan_alert_triggers, alert_project_blocked
from agents.sop_performance_review import schedule_monthly_review
from agents.contract_generator import expire_contract
from core.telegram_bot import send_message


async def check_discount_timeouts() -> list[dict]:
    expired_approvals = await get_expired_approvals()
    results = []

    for approval in expired_approvals:
        if approval.type.value == "DISCOUNT_ESCALATION":
            await update_approval_status(
                approval.approval_id,
                "AUTO_REJECTED",
                datetime.now(timezone.utc).isoformat(),
                "SYSTEM_TIMEOUT",
            )
            results.append({
                "approval_id": approval.approval_id,
                "action": "AUTO_REJECTED",
                "message": (
                    "Mohon maaf kak, setelah kami cek ke manajemen, "
                    "diskon maksimal untuk kali ini hanya 10%. "
                    "Apakah Abang setuju lanjut dengan diskon 10%?"
                ),
            })

            # Raise alert for auto-rejected discount
            from agents.proactive_alerts import alert_discount_auto_rejected
            await alert_discount_auto_rejected(
                project_id=approval.project_id,
                discount_pct=approval.payload.get("discount_pct", 0),
            )

    return results


async def check_contract_reminders() -> list[dict]:
    """Check contracts nearing expiry (H-3 reminder) and expired contracts."""
    results = []

    # H-3 reminder
    expiring_soon = await get_contracts_nearing_expiry(days=3)
    for contract in expiring_soon:
        message = (
            f"⏰ *Contract Reminder H-3*\n"
            f"Contract {contract.contract_id[:8]} ({contract.contract_type.value}) "
            f"for project {contract.project_id[:8]} expires in 3 days.\n"
            f"Client email: {contract.client_email or 'N/A'}"
        )
        try:
            await send_message(message)
            results.append({
                "contract_id": contract.contract_id,
                "action": "REMINDER_SENT",
                "days_until_expiry": 3,
            })
        except Exception as e:
            print(f"Failed to send contract reminder: {e}")

    return results


async def check_contract_escalations() -> list[dict]:
    """Check for expired contracts (>7 days) and escalate to Founder."""
    results = []

    expired_contracts = await get_expired_contracts()
    for contract in expired_contracts:
        # Mark as expired in DB
        await expire_contract(contract.contract_id)

        message = (
            f"🚨 *Contract Expired - Escalation*\n"
            f"Contract {contract.contract_id[:8]} ({contract.contract_type.value}) "
            f"for project {contract.project_id[:8]} has expired (>7 days unsigned).\n"
            f"Client email: {contract.client_email or 'N/A'}\n"
            f"Action required: Follow up with client or cancel."
        )
        try:
            await send_message(message)
            results.append({
                "contract_id": contract.contract_id,
                "action": "ESCALATED",
                "reason": "Expired >7 days unsigned",
            })
        except Exception as e:
            print(f"Failed to send contract escalation: {e}")

    return results


async def run_scheduler_tick() -> dict:
    discount_results = await check_discount_timeouts()
    expired_qris = await expire_old_qris()

    # Send daily report if time
    daily_result = await send_daily_report()

    # Scan for proactive alerts
    alert_results = await scan_alert_triggers()

    # Contract reminders & escalations
    reminder_results = await check_contract_reminders()
    escalation_results = await check_contract_escalations()

    # Monthly review on 1st of month at 09:00
    now = datetime.now(timezone.utc)
    monthly_result = None
    if now.day == 1 and now.hour == 9:
        monthly_result = await schedule_monthly_review()

    return {
        "discount_timeouts": discount_results,
        "expired_qris": expired_qris,
        "daily_report": daily_result,
        "alerts": [a.alert_id for a in alert_results],
        "contract_reminders": reminder_results,
        "contract_escalations": escalation_results,
        "monthly_review": monthly_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }