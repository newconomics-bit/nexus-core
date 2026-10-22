from datetime import datetime, timezone
from database import (
    get_expired_approvals,
    update_approval_status,
)
from agents.payment_verification import expire_old_qris


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

    return results


async def run_scheduler_tick() -> dict:
    discount_results = await check_discount_timeouts()
    expired_qris = await expire_old_qris()

    return {
        "discount_timeouts": discount_results,
        "expired_qris": expired_qris,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }