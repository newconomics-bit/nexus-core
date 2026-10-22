import uuid
from datetime import datetime, timezone
from typing import Callable

from database import (
    get_build_artifact,
    get_build_submission,
    list_audit_reports,
    list_build_artifacts,
    save_audit_finding,
    save_audit_report,
    save_approval,
    update_project_state,
)
from agents.post_mortem import run_post_mortem
from core.telegram_bot import send_approval_card
from models import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditReportStatus,
    BuildArtifact,
    FindingSeverity,
    TaskKind,
)


def _scan_sast(content: str, filename: str) -> list[tuple[str, FindingSeverity, str, str]]:
    findings = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        if "eval(" in line_lower or "exec(" in line_lower:
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.CRITICAL,
                    f"Use of dangerous function (eval/exec) detected",
                    "Avoid eval/exec; use safe alternatives like JSON parsing or explicit logic",
                )
            )
        if "password =" in line_lower and ("=" in line) and not line.strip().startswith("#"):
            if "mock" not in line_lower and "example" not in line_lower:
                findings.append(
                    (
                        f"{filename}:{i}",
                        FindingSeverity.CRITICAL,
                        f"Hardcoded password detected",
                        "Use environment variables or secret management for credentials",
                    )
                )
        if "api_key" in line_lower and "=" in line and not line.strip().startswith("#"):
            if "mock" not in line_lower and "example" not in line_lower:
                findings.append(
                    (
                        f"{filename}:{i}",
                        FindingSeverity.CRITICAL,
                        f"Hardcoded API key detected",
                        "Use environment variables or secret management for API keys",
                    )
                )
        if "secret =" in line_lower and "=" in line and not line.strip().startswith("#"):
            if "mock" not in line_lower and "example" not in line_lower:
                findings.append(
                    (
                        f"{filename}:{i}",
                        FindingSeverity.CRITICAL,
                        f"Hardcoded secret detected",
                        "Use environment variables or secret management for secrets",
                    )
                )
    return findings


def _scan_dast(content: str, filename: str) -> list[tuple[str, FindingSeverity, str, str]]:
    findings = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        if "http://" in line_lower and not line.strip().startswith("#"):
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.HIGH,
                    f"Non-TLS HTTP endpoint detected",
                    "Use HTTPS for all external communications",
                )
            )
        if "debug = true" in line_lower or "debug=true" in line_lower:
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.HIGH,
                    f"Debug mode enabled in configuration",
                    "Disable debug mode in production",
                )
            )
    return findings


def _scan_db_audit(content: str, filename: str) -> list[tuple[str, FindingSeverity, str, str]]:
    findings = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        if "select * from" in line_lower and ("+" in line or "%" in line or "f\"" in line or ".format" in line):
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.HIGH,
                    f"Potential SQL injection via string concatenation",
                    "Use parameterized queries / prepared statements",
                )
            )
        if "drop table" in line_lower:
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.HIGH,
                    f"DROP TABLE statement detected",
                    "Avoid destructive DDL in application code; use migrations",
                )
            )
    return findings


def _scan_osint(content: str, filename: str) -> list[tuple[str, FindingSeverity, str, str]]:
    findings = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        if "0.0.0.0" in line and not line.strip().startswith("#"):
            findings.append(
                (
                    f"{filename}:{i}",
                    FindingSeverity.MEDIUM,
                    f"Binding to 0.0.0.0 exposes service to all interfaces",
                    "Bind to specific interface (e.g., 127.0.0.1) or use firewall rules",
                )
            )
    return findings


SCANNERS: dict[AuditCategory, Callable[[str, str], list[tuple[str, FindingSeverity, str, str]]]] = {
    AuditCategory.SAST: _scan_sast,
    AuditCategory.DAST: _scan_dast,
    AuditCategory.DB_AUDIT: _scan_db_audit,
    AuditCategory.OSINT: _scan_osint,
}


async def run_audit(project_id: str, submission_id: str) -> AuditReport:
    existing_reports = await list_audit_reports(project_id)
    cycle = len(existing_reports) + 1

    artifacts = await list_build_artifacts(project_id)
    submission_artifacts = [a for a in artifacts if a.artifact_id in (await get_submission_artifact_ids(submission_id))]

    all_findings = []

    for artifact in submission_artifacts:
        for category, scanner in SCANNERS.items():
            findings = scanner(artifact.content, artifact.filename)
            for location, severity, description, recommendation in findings:
                finding = AuditFinding(
                    finding_id=str(uuid.uuid4()),
                    project_id=project_id,
                    submission_id=submission_id,
                    category=category,
                    severity=severity,
                    location=location,
                    description=description,
                    recommendation=recommendation,
                )
                await save_audit_finding(finding)
                all_findings.append(finding)

    has_critical_or_high = any(f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) for f in all_findings)

    if has_critical_or_high:
        if cycle < 3:
            report_status = AuditReportStatus.FAILED
            await update_project_state(project_id, "BUILDING")
        else:
            report_status = AuditReportStatus.ESCALATED
            await update_project_state(project_id, "BLOCKED")

            approval = ApprovalRequest(
                approval_id=str(uuid.uuid4()),
                project_id=project_id,
                quote_id="",
                type=ApprovalType.QA_ESCALATION,
                payload={
                    "cycle": cycle,
                    "critical_findings": sum(1 for f in all_findings if f.severity == FindingSeverity.CRITICAL),
                    "high_findings": sum(1 for f in all_findings if f.severity == FindingSeverity.HIGH),
                    "message": f"QA audit failed after {cycle} cycles. Critical/High findings remain.",
                },
                status=ApprovalStatus.PENDING,
                requested_at=datetime.now(timezone.utc).isoformat(),
            )
            await save_approval(approval)
            await send_approval_card(approval)

            await run_post_mortem(project_id)
    else:
        report_status = AuditReportStatus.PASSED
        await update_project_state(project_id, "APPROVED")

    report = AuditReport(
        report_id=str(uuid.uuid4()),
        project_id=project_id,
        submission_id=submission_id,
        cycle=cycle,
        findings=all_findings,
        status=report_status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_audit_report(report)

    if has_critical_or_high and cycle < 3:
        await create_rework_tasks(project_id, submission_id, report)

    return report


async def get_submission_artifact_ids(submission_id: str) -> list[str]:
    from database import get_build_submission
    submission = await get_build_submission(submission_id)
    return submission.artifact_ids if submission else []


async def create_rework_tasks(project_id: str, submission_id: str, report: AuditReport) -> None:
    from agents.engineering_build import breakdown_tasks
    from database import get_project, save_build_task, list_build_tasks
    from models import ProjectSpec, BuildTask, TaskStatus

    project = await get_project(project_id)
    if not project or not project.get("spec_json"):
        return

    spec = ProjectSpec.model_validate_json(project["spec_json"])
    existing_tasks = await list_build_tasks(project_id)

    for finding in report.findings:
        if finding.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH):
            kind = _infer_kind_from_filename(finding.location)
            task = BuildTask(
                task_id=str(uuid.uuid4()),
                project_id=project_id,
                kind=kind,
                title=f"Rework: Fix {finding.category.value} - {finding.description}",
                status=TaskStatus.PENDING,
            )
            await save_build_task(task)


def _infer_kind_from_filename(location: str) -> TaskKind:
    filename = location.split(":")[0].lower()
    if filename.endswith(".tsx") or filename.endswith(".jsx") or filename.endswith(".ts") or filename.endswith(".js"):
        return TaskKind.FRONTEND
    elif filename.endswith(".py"):
        return TaskKind.BACKEND
    elif filename.endswith(".sql"):
        return TaskKind.DATABASE
    return TaskKind.BACKEND