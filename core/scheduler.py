from datetime import datetime, timezone
from database import (
    get_expired_approvals,
    update_approval_status,
)
from agents.payment_verification import expire_old_qris
from agents.daily_report import send_daily_report
from agents.proactive_alerts import scan_alert_triggers


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


async def run_scheduler_tick() -> dict:
    discount_results = await check_discount_timeouts()
    expired_qris = await expire_old_qris()

    # Send daily report if time
    daily_result = await send_daily_report()

    # Scan for proactive alerts
    alert_results = await scan_alert_triggers()

    return {
        "discount_timeouts": discount_results,
        "expired_qris": expired_qris,
        "daily_report": daily_result,
        "alerts": [a.alert_id for a in alert_results],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }