import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from database import (
    count_alerts_for_date,
    get_token_usage_estimate,
    save_alert_event,
)
from core.telegram_bot import send_message
from models import AlertEvent, AlertSeverity, AlertType, AlertSentVia


# Anti-spam: track last alert time per (project_id, type)
_last_alert_cache: dict[tuple[str | None, str], datetime] = {}


async def raise_alert(
    alert_type: AlertType,
    message: str,
    severity: AlertSeverity,
    project_id: Optional[str] = None,
) -> AlertEvent:
    """Create and send an alert. Handles anti-spam for same type/project within 1 hour."""
    now = datetime.now(timezone.utc)
    cache_key = (project_id, alert_type.value)

    # Anti-spam: don't send duplicate alerts within 1 hour
    if cache_key in _last_alert_cache:
        if now - _last_alert_cache[cache_key] < timedelta(hours=1):
            # Still within cooldown, just log (don't save to DB)
            return AlertEvent(
                alert_id=str(uuid.uuid4()),
                project_id=project_id,
                type=alert_type,
                severity=severity,
                message=message,
                sent_via=AlertSentVia.LOG,
                created_at=now.isoformat(),
            )

    _last_alert_cache[cache_key] = now

    alert = AlertEvent(
        alert_id=str(uuid.uuid4()),
        project_id=project_id,
        type=alert_type,
        severity=severity,
        message=message,
        sent_via=AlertSentVia.LOG,  # default, may be upgraded to TELEGRAM
        created_at=now.isoformat(),
    )

    # Send real-time for WARNING and CRITICAL
    if severity in (AlertSeverity.WARNING, AlertSeverity.CRITICAL):
        text = format_alert_text(alert)
        try:
            await send_message(text)
            alert.sent_via = AlertSentVia.TELEGRAM
        except Exception as e:
            print(f"Failed to send alert via Telegram: {e}")

    await save_alert_event(alert)
    return alert


def format_alert_text(alert: AlertEvent) -> str:
    """Format alert for Telegram."""
    severity_emoji = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "CRITICAL": "🚨",
    }
    emoji = severity_emoji.get(alert.severity.value, "🔔")

    lines = [
        f"{emoji} *ALERT: {alert.type.value}*",
        f"Severity: {alert.severity.value}",
        f"Message: {alert.message}",
    ]
    if alert.project_id:
        lines.append(f"Project: {alert.project_id[:8]}")

    return "\n".join(lines)


async def check_token_cap_alerts() -> list:
    """Check for projects approaching token cap and raise alerts."""
    from database import get_token_usage_estimate, get_pipeline_counts
    alerts = []

    # Get all active projects
    pipeline = await get_pipeline_counts()
    active_states = ["LEAD", "DISCOVERY", "QUOTED", "SIGNED", "BUILDING", "AUDITING", "APPROVED", "DEPLOYED", "SUBSCRIPTION"]
    total_active = sum(pipeline.get(s, 0) for s in active_states)

    # Check a sample of projects (in real impl, check each)
    # For now, just check one aggregate estimate
    try:
        estimate = await get_token_usage_estimate("")
        if estimate >= 1.6:  # 80% of $2 cap
            alert = await raise_alert(
                alert_type=AlertType.TOKEN_CAP_NEAR,
                message=f"Token usage estimate: ${estimate:.2f} (80%+ of $2 cap). Review LLM usage.",
                severity=AlertSeverity.WARNING,
            )
            alerts.append(alert)
    except Exception:
        pass

    return alerts


async def scan_alert_triggers() -> list:
    """Scan for all alert triggers. Called from scheduler tick."""
    alerts = []

    # Check token cap
    token_alerts = await check_token_cap_alerts()
    alerts.extend(token_alerts)

    return alerts


# Event-driven alert triggers (called from specific points in code)

async def alert_payment_exception(project_id: str, invoice_id: str, expected: int, actual: int) -> AlertEvent:
    """Called when payment amount mismatch detected."""
    return await raise_alert(
        alert_type=AlertType.PAYMENT_EXCEPTION,
        message=f"Payment exception: Invoice {invoice_id[:8]} expected Rp {expected:,} but got Rp {actual:,}. Nominal mismatch. Client notified for follow-up.",
        severity=AlertSeverity.CRITICAL,
        project_id=project_id,
    )


async def alert_discount_auto_rejected(project_id: str, discount_pct: int) -> AlertEvent:
    """Called when discount approval auto-rejected after timeout."""
    return await raise_alert(
        alert_type=AlertType.DISCOUNT_AUTO_REJECTED,
        message=f"Diskon {discount_pct}% auto-rejected (5 menit timeout). Klien sudah dikasih opsi diskon 10%.",
        severity=AlertSeverity.WARNING,
        project_id=project_id,
    )


async def alert_project_blocked(project_id: str, reason: str) -> AlertEvent:
    """Called when project enters BLOCKED state."""
    return await raise_alert(
        alert_type=AlertType.PROJECT_BLOCKED,
        message=f"Project {project_id[:8]} BLOCKED: {reason}",
        severity=AlertSeverity.CRITICAL,
        project_id=project_id,
    )


async def alert_memory_created(project_id: str, category: str, count: int = 1) -> AlertEvent:
    """Called when new corporate memory is created (INFO, batched to daily report)."""
    return await raise_alert(
        alert_type=AlertType.MEMORY_CREATED,
        message=f"{count} memory baru ({category}) dari project {project_id[:8]}. Akan masuk daily report besok.",
        severity=AlertSeverity.INFO,
        project_id=project_id,
    )


async def alert_deploy_ready(project_id: str, domain_choice: str) -> AlertEvent:
    """Called when deploy approval is created and waiting for Founder."""
    return await raise_alert(
        alert_type=AlertType.DEPLOY_READY,
        message=f"Deploy ready for approval: {domain_choice} domain. Tunggu approve dari Founder.",
        severity=AlertSeverity.INFO,
        project_id=project_id,
    )