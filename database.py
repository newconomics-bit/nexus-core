import json
from datetime import datetime, timezone

import aiosqlite

from models import ApprovalRequest, Quote, BuildArtifact, BuildSubmission, BuildTask, AuditFinding, AuditReport, DeploymentRequest, Invoice, Subscription, QrisRequest, MockLedgerEntry, CorporateMemory, AlertEvent, DailyReport, TechnicalDecision, FeatureRequest, AgentPerformance, Contract, ContractType, ContractStatus, DecisionType, OnboardingPlan, OnboardingItem, OnboardingItemStatus, SupportTicket, TicketCategory, TicketStatus, ClientHealth

DB_PATH = "rakitdigital.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(projects)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "spec_json" not in columns:
            await db.execute("ALTER TABLE projects ADD COLUMN spec_json TEXT")
        if "created_at" not in columns:
            await db.execute("ALTER TABLE projects ADD COLUMN created_at TEXT")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                hpp_breakdown TEXT NOT NULL,
                margin_pct REAL NOT NULL,
                discount_pct REAL NOT NULL,
                final_price INTEGER NOT NULL,
                status TEXT NOT NULL,
                valid_until_days INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                decided_at TEXT NOT NULL DEFAULT '',
                decided_by TEXT NOT NULL DEFAULT '',
                expires_at TEXT
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(approvals)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "expires_at" not in columns:
            await db.execute("ALTER TABLE approvals ADD COLUMN expires_at TEXT")
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS build_tasks (
                task_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                artifact_id TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS build_artifacts (
                artifact_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS build_submissions (
                submission_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                artifact_ids TEXT NOT NULL,
                task_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_findings (
                finding_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                recommendation TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_reports (
                report_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                submission_id TEXT NOT NULL,
                cycle INTEGER NOT NULL,
                findings TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS deployments (
                deployment_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                domain_choice TEXT NOT NULL,
                custom_domain_url TEXT,
                hosted_url TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                paid_at TEXT,
                created_at TEXT
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(invoices)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "created_at" not in columns:
            await db.execute("ALTER TABLE invoices ADD COLUMN created_at TEXT")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                monthly_fee INTEGER NOT NULL,
                status TEXT NOT NULL,
                current_invoice_id TEXT
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS qris_requests (
                qris_id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                qr_string TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS mock_ledger (
                entry_id TEXT PRIMARY KEY,
                reference_code TEXT NOT NULL UNIQUE,
                qris_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                paid_at TEXT NOT NULL
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS corporate_memory (
                memory_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                category TEXT NOT NULL,
                lesson_text TEXT NOT NULL,
                severity TEXT NOT NULL,
                target_agent TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_events (
                alert_id TEXT PRIMARY KEY,
                project_id TEXT,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_via TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_reports (
                report_id TEXT PRIMARY KEY,
                report_date TEXT NOT NULL,
                revenue_today INTEGER NOT NULL,
                pipeline TEXT NOT NULL,
                exceptions TEXT NOT NULL,
                new_memories INTEGER NOT NULL,
                alerts_sent_today INTEGER NOT NULL,
                generated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS technical_decisions (
                decision_id TEXT PRIMARY KEY,
                decision_type TEXT NOT NULL,
                description TEXT NOT NULL,
                impact_score INTEGER NOT NULL,
                requires_founder_approval INTEGER NOT NULL,
                decided_by TEXT NOT NULL,
                decided_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_requests (
                request_id TEXT PRIMARY KEY,
                client_id TEXT,
                description TEXT NOT NULL,
                rice_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                roadmap_target TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_performance (
                agent_name TEXT NOT NULL,
                date TEXT NOT NULL,
                token_usage INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                error_rate REAL NOT NULL,
                tasks_completed INTEGER NOT NULL,
                tasks_failed INTEGER NOT NULL,
                PRIMARY KEY (agent_name, date)
            )
            """
        )
        await db.commit()


    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                template_name TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                sent_at TEXT,
                signed_at TEXT,
                expires_at TEXT,
                created_at TEXT NOT NULL,
                client_email TEXT
            )
            """
        )
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS onboarding_plans (
                plan_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                items_json TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                auto_answered INTEGER NOT NULL DEFAULT 0,
                answer TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS client_health (
                project_id TEXT PRIMARY KEY,
                score INTEGER NOT NULL,
                factors_json TEXT NOT NULL,
                flagged INTEGER NOT NULL DEFAULT 0,
                computed_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def create_project(project_id: str, client_name: str, state: str) -> None:
    from datetime import datetime, timezone
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO projects (id, client_name, state, created_at) VALUES (?, ?, ?, ?)",
            (project_id, client_name, state, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()


async def get_project(project_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, client_name, state, spec_json, created_at FROM projects WHERE id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "client_name": row["client_name"],
            "state": row["state"],
            "spec_json": row["spec_json"],
            "created_at": row["created_at"],
        }


async def save_project_spec(project_id: str, spec_json: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE projects SET spec_json = ? WHERE id = ?",
            (spec_json, project_id),
        )
        await db.commit()


async def update_project_state(project_id: str, new_state: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE projects SET state = ? WHERE id = ?",
            (new_state, project_id),
        )
        await db.commit()


def _row_to_quote(row: aiosqlite.Row) -> Quote:
    return Quote.model_validate(
        {
            "quote_id": row["quote_id"],
            "project_id": row["project_id"],
            "version": row["version"],
            "hpp_breakdown": json.loads(row["hpp_breakdown"]),
            "margin_pct": row["margin_pct"],
            "discount_pct": row["discount_pct"],
            "final_price": row["final_price"],
            "status": row["status"],
            "valid_until_days": row["valid_until_days"],
            "created_at": row["created_at"],
        }
    )


async def save_quote(quote: Quote) -> None:
    payload = quote.model_dump(mode="json")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO quotes (
                quote_id, project_id, version, hpp_breakdown, margin_pct,
                discount_pct, final_price, status, valid_until_days, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(quote_id) DO UPDATE SET
                project_id = excluded.project_id,
                version = excluded.version,
                hpp_breakdown = excluded.hpp_breakdown,
                margin_pct = excluded.margin_pct,
                discount_pct = excluded.discount_pct,
                final_price = excluded.final_price,
                status = excluded.status,
                valid_until_days = excluded.valid_until_days,
                created_at = excluded.created_at
            """,
            (
                payload["quote_id"],
                payload["project_id"],
                payload["version"],
                json.dumps(payload["hpp_breakdown"]),
                payload["margin_pct"],
                payload["discount_pct"],
                payload["final_price"],
                payload["status"],
                payload["valid_until_days"],
                payload["created_at"],
            ),
        )
        await db.commit()


async def get_quote(quote_id: str) -> Quote | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE quote_id = ?",
            (quote_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_quote(row)


async def get_latest_quote(project_id: str) -> Quote | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM quotes
            WHERE project_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_quote(row)


def _row_to_approval(row: aiosqlite.Row) -> ApprovalRequest:
    return ApprovalRequest.model_validate(
        {
            "approval_id": row["approval_id"],
            "project_id": row["project_id"],
            "quote_id": row["quote_id"],
            "type": row["type"],
            "payload": json.loads(row["payload"]),
            "status": row["status"],
            "requested_at": row["requested_at"],
            "decided_at": row["decided_at"],
            "decided_by": row["decided_by"],
            "expires_at": row["expires_at"],
        }
    )


async def save_approval(approval: ApprovalRequest) -> None:
    payload = approval.model_dump(mode="json")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO approvals (
                approval_id, project_id, quote_id, type, payload, status,
                requested_at, decided_at, decided_by, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["approval_id"],
                payload["project_id"],
                payload["quote_id"],
                payload["type"],
                json.dumps(payload["payload"]),
                payload["status"],
                payload["requested_at"],
                payload["decided_at"],
                payload["decided_by"],
                payload.get("expires_at"),
            ),
        )
        await db.commit()


async def get_approval(approval_id: str) -> ApprovalRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM approvals WHERE approval_id = ?",
            (approval_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_approval(row)


async def list_pending_approvals() -> list[ApprovalRequest]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM approvals
            WHERE status = 'PENDING'
            ORDER BY requested_at ASC
            """
        )
        rows = await cursor.fetchall()
        return [_row_to_approval(row) for row in rows]


async def update_approval_status(
    approval_id: str, status: str, decided_at: str, decided_by: str
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE approvals
            SET status = ?, decided_at = ?, decided_by = ?
            WHERE approval_id = ?
            """,
            (status, decided_at, decided_by, approval_id),
        )
        await db.commit()


def _row_to_build_task(row: aiosqlite.Row) -> BuildTask:
    return BuildTask.model_validate(
        {
            "task_id": row["task_id"],
            "project_id": row["project_id"],
            "kind": row["kind"],
            "title": row["title"],
            "status": row["status"],
            "attempts": row["attempts"],
            "artifact_id": row["artifact_id"],
        }
    )


async def save_build_task(task: BuildTask) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO build_tasks (
                task_id, project_id, kind, title, status, attempts, artifact_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                project_id = excluded.project_id,
                kind = excluded.kind,
                title = excluded.title,
                status = excluded.status,
                attempts = excluded.attempts,
                artifact_id = excluded.artifact_id
            """,
            (
                task.task_id,
                task.project_id,
                task.kind.value,
                task.title,
                task.status.value,
                task.attempts,
                task.artifact_id,
            ),
        )
        await db.commit()


async def get_build_task(task_id: str) -> BuildTask | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_tasks WHERE task_id = ?",
            (task_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_build_task(row)


async def list_build_tasks(project_id: str) -> list[BuildTask]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_tasks WHERE project_id = ? ORDER BY task_id",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_build_task(row) for row in rows]


async def update_build_task(task: BuildTask) -> None:
    await save_build_task(task)


def _row_to_build_artifact(row: aiosqlite.Row) -> BuildArtifact:
    return BuildArtifact.model_validate(
        {
            "artifact_id": row["artifact_id"],
            "project_id": row["project_id"],
            "task_id": row["task_id"],
            "filename": row["filename"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
    )


async def save_build_artifact(artifact: BuildArtifact) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO build_artifacts (
                artifact_id, project_id, task_id, filename, content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.artifact_id,
                artifact.project_id,
                artifact.task_id,
                artifact.filename,
                artifact.content,
                artifact.created_at,
            ),
        )
        await db.commit()


async def get_build_artifact(artifact_id: str) -> BuildArtifact | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_artifacts WHERE artifact_id = ?",
            (artifact_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_build_artifact(row)


async def list_build_artifacts(project_id: str) -> list[BuildArtifact]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_artifacts WHERE project_id = ? ORDER BY artifact_id",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_build_artifact(row) for row in rows]


def _row_to_build_submission(row: aiosqlite.Row) -> BuildSubmission:
    import json

    return BuildSubmission.model_validate(
        {
            "submission_id": row["submission_id"],
            "project_id": row["project_id"],
            "artifact_ids": json.loads(row["artifact_ids"]),
            "task_count": row["task_count"],
            "created_at": row["created_at"],
            "status": row["status"],
        }
    )


async def save_build_submission(submission: BuildSubmission) -> None:
    import json

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO build_submissions (
                submission_id, project_id, artifact_ids, task_count, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                submission.submission_id,
                submission.project_id,
                json.dumps(submission.artifact_ids),
                submission.task_count,
                submission.created_at,
                submission.status,
            ),
        )
        await db.commit()


async def get_build_submission(submission_id: str) -> BuildSubmission | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_submissions WHERE submission_id = ?",
            (submission_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_build_submission(row)


async def list_build_submissions(project_id: str) -> list[BuildSubmission]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM build_submissions WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_build_submission(row) for row in rows]


def _row_to_audit_finding(row: aiosqlite.Row) -> AuditFinding:
    return AuditFinding.model_validate(
        {
            "finding_id": row["finding_id"],
            "project_id": row["project_id"],
            "submission_id": row["submission_id"],
            "category": row["category"],
            "severity": row["severity"],
            "location": row["location"],
            "description": row["description"],
            "recommendation": row["recommendation"],
        }
    )


async def save_audit_finding(finding: AuditFinding) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO audit_findings (
                finding_id, project_id, submission_id, category, severity,
                location, description, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding.finding_id,
                finding.project_id,
                finding.submission_id,
                finding.category.value,
                finding.severity.value,
                finding.location,
                finding.description,
                finding.recommendation,
            ),
        )
        await db.commit()


async def list_audit_findings(project_id: str, submission_id: str | None = None) -> list[AuditFinding]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if submission_id:
            cursor = await db.execute(
                "SELECT * FROM audit_findings WHERE project_id = ? AND submission_id = ? ORDER BY finding_id",
                (project_id, submission_id),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM audit_findings WHERE project_id = ? ORDER BY finding_id",
                (project_id,),
            )
        rows = await cursor.fetchall()
        return [_row_to_audit_finding(row) for row in rows]


def _row_to_audit_report(row: aiosqlite.Row) -> AuditReport:
    import json

    return AuditReport.model_validate(
        {
            "report_id": row["report_id"],
            "project_id": row["project_id"],
            "submission_id": row["submission_id"],
            "cycle": row["cycle"],
            "findings": json.loads(row["findings"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }
    )


async def save_audit_report(report: AuditReport) -> None:
    import json

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO audit_reports (
                report_id, project_id, submission_id, cycle, findings, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_id,
                report.project_id,
                report.submission_id,
                report.cycle,
                json.dumps([f.model_dump(mode="json") for f in report.findings]),
                report.status.value,
                report.created_at,
            ),
        )
        await db.commit()


async def get_audit_report(report_id: str) -> AuditReport | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM audit_reports WHERE report_id = ?",
            (report_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_audit_report(row)


async def list_audit_reports(project_id: str) -> list[AuditReport]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM audit_reports WHERE project_id = ? ORDER BY cycle ASC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_audit_report(row) for row in rows]


async def count_audit_reports(project_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM audit_reports WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


def _row_to_deployment(row: aiosqlite.Row) -> DeploymentRequest:
    return DeploymentRequest.model_validate(
        {
            "deployment_id": row["deployment_id"],
            "project_id": row["project_id"],
            "domain_choice": row["domain_choice"],
            "custom_domain_url": row["custom_domain_url"],
            "hosted_url": row["hosted_url"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
    )


async def save_deployment(deployment: DeploymentRequest) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO deployments (
                deployment_id, project_id, domain_choice, custom_domain_url, hosted_url, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(deployment_id) DO UPDATE SET
                project_id = excluded.project_id,
                domain_choice = excluded.domain_choice,
                custom_domain_url = excluded.custom_domain_url,
                hosted_url = excluded.hosted_url,
                status = excluded.status,
                created_at = excluded.created_at
            """,
            (
                deployment.deployment_id,
                deployment.project_id,
                deployment.domain_choice.value,
                deployment.custom_domain_url,
                deployment.hosted_url,
                deployment.status.value,
                deployment.created_at,
            ),
        )
        await db.commit()


async def get_deployment(deployment_id: str) -> DeploymentRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deployments WHERE deployment_id = ?",
            (deployment_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_deployment(row)


async def get_deployment_by_project(project_id: str) -> DeploymentRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deployments WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_deployment(row)


def _row_to_invoice(row: aiosqlite.Row) -> Invoice:
    return Invoice.model_validate(
        {
            "invoice_id": row["invoice_id"],
            "project_id": row["project_id"],
            "amount": row["amount"],
            "due_date": row["due_date"],
            "status": row["status"],
            "paid_at": row["paid_at"],
        }
    )


async def save_invoice(invoice: Invoice) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO invoices (
                invoice_id, project_id, amount, due_date, status, paid_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_id) DO UPDATE SET
                project_id = excluded.project_id,
                amount = excluded.amount,
                due_date = excluded.due_date,
                status = excluded.status,
                paid_at = excluded.paid_at,
                created_at = excluded.created_at
            """,
            (
                invoice.invoice_id,
                invoice.project_id,
                invoice.amount,
                invoice.due_date,
                invoice.status.value,
                invoice.paid_at,
                invoice.created_at,
            ),
        )
        await db.commit()


async def get_invoice(invoice_id: str) -> Invoice | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_invoice(row)


async def list_invoices(project_id: str) -> list[Invoice]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM invoices WHERE project_id = ? ORDER BY due_date ASC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_invoice(row) for row in rows]


async def list_all_invoices() -> list[Invoice]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM invoices ORDER BY due_date ASC",
        )
        rows = await cursor.fetchall()
        return [_row_to_invoice(row) for row in rows]


async def get_overdue_invoices() -> list[Invoice]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM invoices WHERE status = 'PENDING' AND due_date < ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
        rows = await cursor.fetchall()
        return [_row_to_invoice(row) for row in rows]


def _row_to_subscription(row: aiosqlite.Row) -> Subscription:
    return Subscription.model_validate(
        {
            "subscription_id": row["subscription_id"],
            "project_id": row["project_id"],
            "monthly_fee": row["monthly_fee"],
            "status": row["status"],
            "current_invoice_id": row["current_invoice_id"],
        }
    )


async def save_subscription(subscription: Subscription) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO subscriptions (
                subscription_id, project_id, monthly_fee, status, current_invoice_id
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subscription_id) DO UPDATE SET
                project_id = excluded.project_id,
                monthly_fee = excluded.monthly_fee,
                status = excluded.status,
                current_invoice_id = excluded.current_invoice_id
            """,
            (
                subscription.subscription_id,
                subscription.project_id,
                subscription.monthly_fee,
                subscription.status.value,
                subscription.current_invoice_id,
            ),
        )
        await db.commit()


async def get_subscription(project_id: str) -> Subscription | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscriptions WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_subscription(row)


def _row_to_qris(row: aiosqlite.Row) -> QrisRequest:
    return QrisRequest.model_validate(
        {
            "qris_id": row["qris_id"],
            "invoice_id": row["invoice_id"],
            "amount": row["amount"],
            "qr_string": row["qr_string"],
            "status": row["status"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        }
    )


async def save_qris(qris: QrisRequest) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO qris_requests (
                qris_id, invoice_id, amount, qr_string, status, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(qris_id) DO UPDATE SET
                invoice_id = excluded.invoice_id,
                amount = excluded.amount,
                qr_string = excluded.qr_string,
                status = excluded.status,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (
                qris.qris_id,
                qris.invoice_id,
                qris.amount,
                qris.qr_string,
                qris.status.value,
                qris.created_at,
                qris.expires_at,
            ),
        )
        await db.commit()


async def get_qris(qris_id: str) -> QrisRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM qris_requests WHERE qris_id = ?",
            (qris_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_qris(row)


async def get_qris_by_invoice(invoice_id: str) -> QrisRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM qris_requests WHERE invoice_id = ? ORDER BY created_at DESC LIMIT 1",
            (invoice_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_qris(row)


async def get_expired_qris() -> list[QrisRequest]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM qris_requests WHERE status = 'ACTIVE' AND expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
        rows = await cursor.fetchall()
        return [_row_to_qris(row) for row in rows]


def _row_to_ledger(row: aiosqlite.Row) -> MockLedgerEntry:
    return MockLedgerEntry.model_validate(
        {
            "entry_id": row["entry_id"],
            "reference_code": row["reference_code"],
            "qris_id": row["qris_id"],
            "amount": row["amount"],
            "paid_at": row["paid_at"],
        }
    )


async def save_ledger_entry(entry: MockLedgerEntry) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO mock_ledger (
                entry_id, reference_code, qris_id, amount, paid_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.reference_code,
                entry.qris_id,
                entry.amount,
                entry.paid_at,
            ),
        )
        await db.commit()


async def get_ledger_by_reference(reference_code: str) -> MockLedgerEntry | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM mock_ledger WHERE reference_code = ?",
            (reference_code,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_ledger(row)


async def get_ledger_by_qris(qris_id: str) -> list[MockLedgerEntry]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM mock_ledger WHERE qris_id = ?",
            (qris_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_ledger(row) for row in rows]


async def get_expired_approvals() -> list[ApprovalRequest]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM approvals
            WHERE status = 'PENDING' AND expires_at IS NOT NULL AND expires_at < ?
            ORDER BY requested_at ASC
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )
        rows = await cursor.fetchall()
        return [_row_to_approval(row) for row in rows]


def _row_to_corporate_memory(row: aiosqlite.Row) -> CorporateMemory:
    return CorporateMemory.model_validate(
        {
            "memory_id": row["memory_id"],
            "project_id": row["project_id"],
            "category": row["category"],
            "lesson_text": row["lesson_text"],
            "severity": row["severity"],
            "target_agent": row["target_agent"],
            "created_at": row["created_at"],
        }
    )


async def save_corporate_memory(memory: CorporateMemory) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO corporate_memory (
                memory_id, project_id, category, lesson_text, severity, target_agent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.memory_id,
                memory.project_id,
                memory.category.value,
                memory.lesson_text,
                memory.severity.value,
                memory.target_agent,
                memory.created_at,
            ),
        )
        await db.commit()


async def get_memories_by_agent(target_agent: str) -> list[CorporateMemory]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM corporate_memory WHERE target_agent = ? ORDER BY created_at DESC",
            (target_agent,),
        )
        rows = await cursor.fetchall()
        return [_row_to_corporate_memory(row) for row in rows]


async def get_memories_by_project(project_id: str) -> list[CorporateMemory]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM corporate_memory WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_corporate_memory(row) for row in rows]


def _row_to_alert_event(row: aiosqlite.Row) -> AlertEvent:
    return AlertEvent.model_validate(
        {
            "alert_id": row["alert_id"],
            "project_id": row["project_id"],
            "type": row["type"],
            "severity": row["severity"],
            "message": row["message"],
            "sent_via": row["sent_via"],
            "created_at": row["created_at"],
            "acknowledged": bool(row["acknowledged"]),
        }
    )


async def save_alert_event(alert: AlertEvent) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO alert_events (
                alert_id, project_id, type, severity, message, sent_via, created_at, acknowledged
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.alert_id,
                alert.project_id,
                alert.type.value,
                alert.severity.value,
                alert.message,
                alert.sent_via.value,
                alert.created_at,
                int(alert.acknowledged),
            ),
        )
        await db.commit()


async def get_alert_event(alert_id: str) -> AlertEvent | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM alert_events WHERE alert_id = ?",
            (alert_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_alert_event(row)


async def get_unacknowledged_alerts() -> list[AlertEvent]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM alert_events WHERE acknowledged = 0 ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [_row_to_alert_event(row) for row in rows]


async def acknowledge_alert(alert_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE alert_events SET acknowledged = 1 WHERE alert_id = ?",
            (alert_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


async def count_alerts_for_date(date_str: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM alert_events WHERE date(created_at) = date(?)",
            (date_str,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


def _row_to_daily_report(row: aiosqlite.Row) -> DailyReport:
    import json
    return DailyReport.model_validate(
        {
            "report_id": row["report_id"],
            "report_date": row["report_date"],
            "revenue_today": row["revenue_today"],
            "pipeline": json.loads(row["pipeline"]),
            "exceptions": json.loads(row["exceptions"]),
            "new_memories": row["new_memories"],
            "alerts_sent_today": row["alerts_sent_today"],
            "generated_at": row["generated_at"],
        }
    )


async def save_daily_report(report: DailyReport) -> None:
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO daily_reports (
                report_id, report_date, revenue_today, pipeline, exceptions,
                new_memories, alerts_sent_today, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_id,
                report.report_date,
                report.revenue_today,
                json.dumps(report.pipeline),
                json.dumps(report.exceptions),
                report.new_memories,
                report.alerts_sent_today,
                report.generated_at,
            ),
        )
        await db.commit()


async def get_daily_report(report_date: str) -> DailyReport | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM daily_reports WHERE report_date = ?",
            (report_date,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_daily_report(row)


async def get_revenue_for_date(date_str: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'PAID' AND date(paid_at) = date(?)",
            (date_str,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_pipeline_counts() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT state, COUNT(*) FROM projects GROUP BY state"
        )
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}


async def count_memories_created_on(date_str: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM corporate_memory WHERE date(created_at) = date(?)",
            (date_str,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_invoices_with_exception_on_date(date_str: str) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT invoice_id, project_id FROM invoices 
            WHERE status = 'PAYMENT_EXCEPTION' AND date(created_at) = date(?)
            """,
            (date_str,),
        )
        rows = await cursor.fetchall()
        return [
            f"Invoice {row[0][:8]} ({row[1][:8]}): nominal mismatch"
            for row in rows
        ]


async def get_token_usage_estimate(project_id: str) -> float:
    """Mock token usage estimate - returns a value that can be monkeypatched for testing."""
    return 0.0


async def get_last_report_date() -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT report_date FROM daily_reports ORDER BY generated_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def save_last_report_date(report_date: str) -> None:
    """Track last report date to prevent duplicate reports."""
    pass  # Using daily_reports table for this


async def list_alert_events(acknowledged: bool | None = None) -> list[AlertEvent]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if acknowledged is None:
            query = "SELECT * FROM alert_events ORDER BY created_at DESC"
            params = ()
        elif acknowledged:
            query = "SELECT * FROM alert_events WHERE acknowledged = 1 ORDER BY created_at DESC"
            params = ()
        else:
            query = "SELECT * FROM alert_events WHERE acknowledged = 0 ORDER BY created_at DESC"
            params = ()
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_alert_event(row) for row in rows]


def _row_to_technical_decision(row: aiosqlite.Row) -> TechnicalDecision:
    return TechnicalDecision.model_validate(
        {
            "decision_id": row["decision_id"],
            "decision_type": row["decision_type"],
            "description": row["description"],
            "impact_score": row["impact_score"],
            "requires_founder_approval": bool(row["requires_founder_approval"]),
            "decided_by": row["decided_by"],
            "decided_at": row["decided_at"],
            "status": row["status"],
        }
    )


async def save_technical_decision(decision: TechnicalDecision) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO technical_decisions (
                decision_id, decision_type, description, impact_score,
                requires_founder_approval, decided_by, decided_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.decision_type.value,
                decision.description,
                decision.impact_score,
                int(decision.requires_founder_approval),
                decision.decided_by,
                decision.decided_at,
                decision.status.value,
            ),
        )
        await db.commit()


async def get_technical_decision(decision_id: str) -> TechnicalDecision | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM technical_decisions WHERE decision_id = ?",
            (decision_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_technical_decision(row)


async def get_technical_decisions_by_type(decision_type: DecisionType) -> list[TechnicalDecision]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM technical_decisions WHERE decision_type = ? ORDER BY decided_at DESC",
            (decision_type.value,),
        )
        rows = await cursor.fetchall()
        return [_row_to_technical_decision(row) for row in rows]


def _row_to_feature_request(row: aiosqlite.Row) -> FeatureRequest:
    return FeatureRequest.model_validate(
        {
            "request_id": row["request_id"],
            "client_id": row["client_id"],
            "description": row["description"],
            "rice_score": row["rice_score"],
            "status": row["status"],
            "evaluated_at": row["evaluated_at"],
            "roadmap_target": row["roadmap_target"],
        }
    )


async def save_feature_request(request: FeatureRequest) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO feature_requests (
                request_id, client_id, description, rice_score, status, evaluated_at, roadmap_target
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.request_id,
                request.client_id,
                request.description,
                request.rice_score,
                request.status.value,
                request.evaluated_at,
                request.roadmap_target,
            ),
        )
        await db.commit()


async def get_feature_request(request_id: str) -> FeatureRequest | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM feature_requests WHERE request_id = ?",
            (request_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_feature_request(row)


async def get_pending_feature_requests() -> list[FeatureRequest]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM feature_requests WHERE status = 'SUBMITTED' ORDER BY evaluated_at DESC"
        )
        rows = await cursor.fetchall()
        return [_row_to_feature_request(row) for row in rows]


def _row_to_agent_performance(row: aiosqlite.Row) -> AgentPerformance:
    return AgentPerformance.model_validate(
        {
            "agent_name": row["agent_name"],
            "date": row["date"],
            "token_usage": row["token_usage"],
            "success_rate": row["success_rate"],
            "error_rate": row["error_rate"],
            "tasks_completed": row["tasks_completed"],
            "tasks_failed": row["tasks_failed"],
        }
    )


async def save_agent_performance(performance: AgentPerformance) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_performance (
                agent_name, date, token_usage, success_rate, error_rate,
                tasks_completed, tasks_failed
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name, date) DO UPDATE SET
                token_usage = excluded.token_usage,
                success_rate = excluded.success_rate,
                error_rate = excluded.error_rate,
                tasks_completed = excluded.tasks_completed,
                tasks_failed = excluded.tasks_failed
            """,
            (
                performance.agent_name,
                performance.date,
                performance.token_usage,
                performance.success_rate,
                performance.error_rate,
                performance.tasks_completed,
                performance.tasks_failed,
            ),
        )
        await db.commit()


async def get_agent_performance_last_30_days() -> list[AgentPerformance]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM agent_performance WHERE date >= ? ORDER BY date DESC",
            (cutoff,),
        )
        rows = await cursor.fetchall()
        return [_row_to_agent_performance(row) for row in rows]


def _row_to_contract(row: aiosqlite.Row) -> Contract:
    return Contract.model_validate(
        {
            "contract_id": row["contract_id"],
            "project_id": row["project_id"],
            "contract_type": row["contract_type"],
            "template_name": row["template_name"],
            "content": row["content"],
            "status": row["status"],
            "sent_at": row["sent_at"],
            "signed_at": row["signed_at"],
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
            "client_email": row["client_email"],
        }
    )


async def save_contract(contract: Contract) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO contracts (
                contract_id, project_id, contract_type, template_name, content,
                status, sent_at, signed_at, expires_at, created_at, client_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(contract_id) DO UPDATE SET
                project_id = excluded.project_id,
                contract_type = excluded.contract_type,
                template_name = excluded.template_name,
                content = excluded.content,
                status = excluded.status,
                sent_at = excluded.sent_at,
                signed_at = excluded.signed_at,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at,
                client_email = excluded.client_email
            """,
            (
                contract.contract_id,
                contract.project_id,
                contract.contract_type.value,
                contract.template_name,
                contract.content,
                contract.status.value,
                contract.sent_at,
                contract.signed_at,
                contract.expires_at,
                contract.created_at,
                contract.client_email,
            ),
        )
        await db.commit()


async def get_contract(contract_id: str) -> Contract | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM contracts WHERE contract_id = ?",
            (contract_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_contract(row)


async def list_contracts(project_id: str | None = None) -> list[Contract]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if project_id:
            cursor = await db.execute(
                "SELECT * FROM contracts WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM contracts ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        return [_row_to_contract(row) for row in rows]


async def get_pending_contracts() -> list[Contract]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM contracts WHERE status = 'SENT' AND expires_at IS NOT NULL ORDER BY expires_at ASC"
        )
        rows = await cursor.fetchall()
        return [_row_to_contract(row) for row in rows]


async def get_contracts_nearing_expiry(days: int = 3) -> list[Contract]:
    from datetime import date, timedelta
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM contracts
            WHERE status = 'SENT' AND expires_at IS NOT NULL
            AND date(expires_at) <= date(?)
            ORDER BY expires_at ASC
            """,
            (cutoff,),
        )
        rows = await cursor.fetchall()
        return [_row_to_contract(row) for row in rows]


async def get_expired_contracts() -> list[Contract]:
    from datetime import date
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM contracts WHERE status = 'SENT' AND expires_at IS NOT NULL AND date(expires_at) < date(?)",
            (today,),
        )
        rows = await cursor.fetchall()
        return [_row_to_contract(row) for row in rows]


async def list_alert_events(acknowledged: bool | None = None) -> list[AlertEvent]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if acknowledged is None:
            query = "SELECT * FROM alert_events ORDER BY created_at DESC"
            params = ()
        elif acknowledged:
            query = "SELECT * FROM alert_events WHERE acknowledged = 1 ORDER BY created_at DESC"
            params = ()
        else:
            query = "SELECT * FROM alert_events WHERE acknowledged = 0 ORDER BY created_at DESC"
            params = ()
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_alert_event(row) for row in rows]


async def get_active_client_projects() -> list[dict]:
    """Get all active client projects (SUBSCRIPTION or DEPLOYED state)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, client_name, state, created_at FROM projects WHERE state IN ('SUBSCRIPTION', 'DEPLOYED')"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


def _row_to_onboarding_plan(row: aiosqlite.Row) -> OnboardingPlan:
    import json
    return OnboardingPlan.model_validate(
        {
            "plan_id": row["plan_id"],
            "project_id": row["project_id"],
            "created_at": row["created_at"],
            "items": json.loads(row["items_json"]),
        }
    )


async def save_onboarding_plan(plan: OnboardingPlan) -> None:
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO onboarding_plans (
                plan_id, project_id, created_at, items_json
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(plan_id) DO UPDATE SET
                project_id = excluded.project_id,
                created_at = excluded.created_at,
                items_json = excluded.items_json
            """,
            (
                plan.plan_id,
                plan.project_id,
                plan.created_at,
                json.dumps([item.model_dump(mode="json") for item in plan.items]),
            ),
        )
        await db.commit()


async def get_onboarding_plan(project_id: str) -> OnboardingPlan | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM onboarding_plans WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_onboarding_plan(row)


async def update_onboarding_item(item_id: str, status: str, completed_at: str | None = None) -> None:
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM onboarding_plans WHERE items_json LIKE ?",
            (f"%{item_id}%",),
        )
        row = await cursor.fetchone()
        if row is None:
            return
        plan = _row_to_onboarding_plan(row)
        for item in plan.items:
            if item.item_id == item_id:
                item.status = OnboardingItemStatus(status)
                if completed_at:
                    item.completed_at = completed_at
                break
        await save_onboarding_plan(plan)


def _row_to_support_ticket(row: aiosqlite.Row) -> SupportTicket:
    return SupportTicket.model_validate(
        {
            "ticket_id": row["ticket_id"],
            "project_id": row["project_id"],
            "category": row["category"],
            "description": row["description"],
            "status": row["status"],
            "auto_answered": bool(row["auto_answered"]),
            "answer": row["answer"],
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
        }
    )


async def save_support_ticket(ticket: SupportTicket) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO support_tickets (
                ticket_id, project_id, category, description, status,
                auto_answered, answer, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                project_id = excluded.project_id,
                category = excluded.category,
                description = excluded.description,
                status = excluded.status,
                auto_answered = excluded.auto_answered,
                answer = excluded.answer,
                created_at = excluded.created_at,
                resolved_at = excluded.resolved_at
            """,
            (
                ticket.ticket_id,
                ticket.project_id,
                ticket.category.value,
                ticket.description,
                ticket.status.value,
                int(ticket.auto_answered),
                ticket.answer,
                ticket.created_at,
                ticket.resolved_at,
            ),
        )
        await db.commit()


async def get_support_ticket(ticket_id: str) -> SupportTicket | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE ticket_id = ?",
            (ticket_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_support_ticket(row)


async def list_support_tickets(project_id: str | None = None, status: str | None = None) -> list[SupportTicket]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM support_tickets WHERE 1=1"
        params = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()
        return [_row_to_support_ticket(row) for row in rows]


def _row_to_client_health(row: aiosqlite.Row) -> ClientHealth:
    import json
    return ClientHealth.model_validate(
        {
            "project_id": row["project_id"],
            "score": row["score"],
            "factors": json.loads(row["factors_json"]),
            "flagged": bool(row["flagged"]),
            "computed_at": row["computed_at"],
        }
    )


async def save_client_health(health: ClientHealth) -> None:
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO client_health (
                project_id, score, factors_json, flagged, computed_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                score = excluded.score,
                factors_json = excluded.factors_json,
                flagged = excluded.flagged,
                computed_at = excluded.computed_at
            """,
            (
                health.project_id,
                health.score,
                json.dumps(health.factors),
                int(health.flagged),
                health.computed_at,
            ),
        )
        await db.commit()


async def get_client_health(project_id: str) -> ClientHealth | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM client_health WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_client_health(row)


async def list_client_health(flagged: bool | None = None) -> list[ClientHealth]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM client_health WHERE 1=1"
        params = []
        if flagged is not None:
            query += " AND flagged = ?"
            params.append(int(flagged))
        query += " ORDER BY computed_at DESC"
        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()
        return [_row_to_client_health(row) for row in rows]
