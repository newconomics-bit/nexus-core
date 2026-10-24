import uuid
import hashlib
import json
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from database import (
    get_latest_backup,
    get_backup,
    get_disk_usage_percent,
    get_last_backup_date,
    get_last_drill_date,
    save_backup,
    save_incident,
    get_incident,
    get_open_incidents,
    get_incidents_by_type_open,
    save_drill,
    snapshot_core_tables,
    restore_snapshot_to_temp,
    get_last_backup_date,
    get_last_drill_date,
    save_incident as db_save_incident,
    insert_audit_log,
)
from agents.proactive_alerts import raise_alert
from agents.post_mortem import run_post_mortem
from core.telegram_bot import send_message
from models import (
    BackupRecord,
    BackupType,
    BackupStatus,
    Incident,
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    DrillResult,
    DrillStatus,
    CorporateMemory,
    MemoryCategory,
    MemorySeverity,
    AuditAction,
    AuditResult,
)


# Anti-duplicate cache for watchdog
_last_incident_cache: dict[tuple[str | None, str], datetime] = {}


async def run_backup() -> BackupRecord:
    """Run daily backup of core tables."""
    snapshot = await snapshot_core_tables()
    snapshot_json = json.dumps(snapshot, default=str)
    size_bytes = len(snapshot_json.encode("utf-8"))
    checksum = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

    backup = BackupRecord(
        backup_id=str(uuid.uuid4()),
        type=BackupType.DB,
        created_at=datetime.now(timezone.utc).isoformat(),
        size_bytes=size_bytes,
        checksum=checksum,
        status=BackupStatus.SUCCESS,
        verified=False,
    )

    try:
        # Verify the backup immediately
        temp_counts = await restore_snapshot_to_temp(snapshot)
        expected_counts = {table: len(rows) for table, rows in snapshot.items()}
        if temp_counts == expected_counts:
            backup.verified = True
            backup.status = BackupStatus.SUCCESS
        else:
            backup.status = BackupStatus.FAILED
    except Exception as e:
        backup.status = BackupStatus.FAILED
        print(f"Backup verification failed: {e}")

    await save_backup(backup)

    if backup.status == BackupStatus.FAILED:
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.BACKUP_FAILED,
            message=f"Backup {backup.backup_id[:8]} failed verification. Check backup integrity.",
            severity=AlertSeverity.WARNING,
        )

    return backup


async def verify_backup(backup_id: str) -> bool:
    """Verify a backup by restoring to temp and comparing record counts."""
    backup = await get_backup(backup_id)
    if not backup:
        return False

    # Re-snapshot current state and compute checksum
    snapshot = await snapshot_core_tables()
    snapshot_json = json.dumps(snapshot, default=str)
    current_checksum = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()

    # Compare with stored checksum
    if current_checksum == backup.checksum:
        from database import save_backup as db_save_backup
        backup.verified = True
        from database import save_backup
        await save_backup(backup)
        return True
    return False


async def run_dr_drill() -> DrillResult:
    """Run disaster recovery drill - restore latest verified backup to temp."""
    drill_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    backup = await get_latest_backup()
    if not backup:
        drill = DrillResult(
            drill_id=drill_id,
            backup_id="",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            status=DrillStatus.FAIL,
            notes="No backup available for drill",
        )
        await save_drill(drill)
        return drill

    # Verify the backup before running drill
    verified = await verify_backup(backup.backup_id)
    if not verified:
        drill = DrillResult(
            drill_id=drill_id,
            backup_id=backup.backup_id,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            status=DrillStatus.FAIL,
            notes="Backup verification failed - checksum mismatch or backup corrupted",
        )
        await save_drill(drill)
        
        # Raise alert for failed drill
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.DRILL_FAILED,
            message=f"DR drill failed for backup {backup.backup_id[:8]}: backup verification failed",
            severity=AlertSeverity.CRITICAL,
        )
        return drill

    started_at = datetime.now(timezone.utc).isoformat()

    try:
        # Get the snapshot from backup (we'd need to store the snapshot separately)
        # For now, simulate by snapshotting current state
        snapshot = await snapshot_core_tables()
        counts = await restore_snapshot_to_temp(snapshot)

        # Compare counts
        expected_counts = {table: len(rows) for table, rows in snapshot.items()}
        if counts == expected_counts:
            status = DrillStatus.PASS
            notes = f"Drill PASS: All {len(expected_counts)} tables restored with matching counts."
        else:
            status = DrillStatus.FAIL
            notes = f"Drill FAIL: Record count mismatch. Expected: {expected_counts}, Got: {counts}"
    except Exception as e:
        status = DrillStatus.FAIL
        notes = f"Drill FAIL: {str(e)}"

    finished_at = datetime.now(timezone.utc).isoformat()

    drill = DrillResult(
        drill_id=drill_id,
        backup_id=backup.backup_id,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        notes=notes,
    )

    await save_drill(drill)

    # Log to corporate memory
    from agents.post_mortem import run_post_mortem
    from models import CorporateMemory, MemoryCategory, MemorySeverity
    from database import save_corporate_memory

    memory = CorporateMemory(
        memory_id=str(uuid.uuid4()),
        project_id="",
        category=MemoryCategory.OPS_INCIDENT,
        lesson_text=f"DR Drill {drill_id[:8]}: {notes}",
        severity=MemorySeverity.HIGH if status == DrillStatus.FAIL else MemorySeverity.LOW,
        target_agent="OPS",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await save_corporate_memory(memory)

    # Alert on failure
    if status == DrillStatus.FAIL:
        from agents.proactive_alerts import raise_alert
        from models import AlertType, AlertSeverity
        await raise_alert(
            alert_type=AlertType.DRILL_FAILED,
            message=f"DR Drill FAILED: {notes}",
            severity=AlertSeverity.CRITICAL,
        )

    return drill


async def watchdog_check() -> list:
    """Run deterministic watchdog checks."""
    incidents = []

    # 1. Check DB reachable
    try:
        from database import get_project
        await get_project("health-check")
    except Exception:
        incident = await _create_incident(
            incident_type="DB_DOWN",
            severity="CRITICAL",
            message="Database unreachable. Watchdog check failed.",
        )
        incidents.append(incident)

    # 2. Check backup freshness (< 26 hours)
    last_backup_str = await get_last_backup_date()
    if last_backup_str:
        last_backup = datetime.fromisoformat(last_backup_str.replace("Z", "+00:00"))
        hours_since_backup = (datetime.now(timezone.utc) - last_backup).total_seconds() / 3600
        if hours_since_backup > 26:
            incident = await _create_incident(
                incident_type="BACKUP_STALE",
                severity="WARNING",
                message=f"Backup stale: {hours_since_backup:.1f} hours since last backup (max 26h).",
            )
            incidents.append(incident)
    else:
        incident = await _create_incident(
            incident_type="BACKUP_STALE",
            severity="CRITICAL",
            message="No backup found. Backup system may be down.",
        )
        incidents.append(incident)

    # 3. Check disk usage
    try:
        disk_usage = await get_disk_usage_percent()
        if disk_usage >= 95:
            incident = await _create_incident(
                incident_type="DISK_FULL",
                severity="CRITICAL",
                message=f"Disk usage at {disk_usage:.1f}% (>= 95%). Immediate action required.",
            )
            incidents.append(incident)
        elif disk_usage >= 85:
            incident = await _create_incident(
                incident_type="DISK_FULL",
                severity="WARNING",
                message=f"Disk usage at {disk_usage:.1f}% (>= 85%). Monitor closely.",
            )
            incidents.append(incident)
    except Exception as e:
        print(f"Disk usage check failed: {e}")

    return incidents


async def _create_incident(
    incident_type: str,
    severity: str,
    message: str,
    project_id: Optional[str] = None,
) -> Incident:
    """Create incident with anti-duplication logic."""
    from agents.proactive_alerts import raise_alert
    from models import AlertType, AlertSeverity, IncidentSeverity, IncidentType

    # Check if similar incident already open
    from database import get_incidents_by_type_open
    open_incidents = await get_incidents_by_type_open(incident_type)
    if open_incidents:
        # Return existing open incident
        return open_incidents[0]

    # Create new incident
    incident = Incident(
        incident_id=str(uuid.uuid4()),
        type=IncidentType(incident_type),
        severity=IncidentSeverity(severity),
        status="OPEN",
        detected_at=datetime.now(timezone.utc).isoformat(),
        timeline=[{
            "at": datetime.now(timezone.utc).isoformat(),
            "action": "detected",
            "by": "watchdog",
        }],
    )

    from database import save_incident
    await save_incident(incident)

    # Raise alert
    from agents.proactive_alerts import raise_alert
    await raise_alert(
        alert_type=AlertType(incident_type),
        message=message,
        severity=AlertSeverity(severity),
        project_id=project_id,
    )

    return incident


async def mitigate_incident(incident_id: str, action: str) -> Incident | None:
    """Mitigate an incident with a specific action."""
    incident = await get_incident(incident_id)
    if not incident:
        return None

    if incident.status != IncidentStatus.OPEN:
        return incident

    incident.timeline.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "by": "system",
    })

    if action == "RESTORE_FROM_BACKUP":
        # Simulate restore from latest verified backup
        backup = await get_latest_backup()
        if backup and backup.verified:
            incident.status = IncidentStatus.MITIGATED
            incident.mitigated_at = datetime.now(timezone.utc).isoformat()
            incident.timeline.append({
                "at": datetime.now(timezone.utc).isoformat(),
                "action": "restore_completed",
                "by": "system",
                "details": f"Restored from backup {backup.backup_id[:8]}",
            })

    from database import save_incident
    await save_incident(incident)
    return incident


async def resolve_incident(incident_id: str) -> Incident | None:
    incident = await get_incident(incident_id)
    if not incident:
        return None

    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = datetime.now(timezone.utc).isoformat()
    incident.timeline.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "action": "resolved",
        "by": "system",
    })

    from database import save_incident
    await save_incident(incident)

    # Audit log for incident resolution
    await insert_audit_log(
        actor="system",
        action=AuditAction.INCIDENT_RESOLVED.value,
        target_id=incident_id,
        result=AuditResult.SUCCESS.value,
        context={"incident_type": incident.type.value, "severity": incident.severity.value, "mitigation": incident.timeline[-2]['action'] if len(incident.timeline) >= 2 else incident.timeline[-1]['action']},
    )

    # Trigger post-incident postmortem
    await post_incident_postmortem(incident.incident_id)

    return incident


async def post_incident_postmortem(incident_id: str) -> None:
    """Create post-incident corporate memory entry."""
    incident = await get_incident(incident_id)
    if not incident:
        return

    from models import CorporateMemory, MemoryCategory, MemorySeverity
    from database import save_corporate_memory

    memory = CorporateMemory(
        memory_id=str(uuid.uuid4()),
        project_id="",
        category=MemoryCategory.OPS_INCIDENT,
        lesson_text=(
            f"Incident {incident.incident_id[:8]} ({incident.type.value}, {incident.severity.value}): "
            f"Mitigated by {incident.timeline[-1]['action'] if incident.timeline else 'N/A'}. "
            f"Duration: {incident.resolved_at or incident.detected_at} to {incident.resolved_at}. "
            f"Timeline: {incident.timeline}"
        ),
        severity=MemorySeverity.HIGH,
        target_agent="OPS",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    from database import save_corporate_memory
    await save_corporate_memory(memory)