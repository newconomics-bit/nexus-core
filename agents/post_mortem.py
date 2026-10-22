import uuid
from datetime import datetime, timezone

from database import (
    get_project,
    list_audit_reports,
    list_invoices,
    save_corporate_memory,
)
from models import CorporateMemory, MemoryCategory, MemorySeverity


async def run_post_mortem(project_id: str) -> list[CorporateMemory]:
    project = await get_project(project_id)
    if not project:
        raise ValueError("Project not found")

    final_state = project["state"]

    audit_reports = await list_audit_reports(project_id)
    audit_cycles = len(audit_reports)

    invoices = await list_invoices(project_id)
    has_payment_exception = any(
        inv.status.value == "PAYMENT_EXCEPTION" for inv in invoices
    )

    memories_to_save = []

    if audit_cycles >= 2:
        memory = CorporateMemory(
            memory_id=str(uuid.uuid4()),
            project_id=project_id,
            category=MemoryCategory.CODING_MISTAKE,
            lesson_text="Kode sering rework di QA. Pastikan validasi input dan edge cases sebelum submit.",
            severity=MemorySeverity.HIGH,
            target_agent="CODER",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        memories_to_save.append(memory)

    if has_payment_exception:
        memory = CorporateMemory(
            memory_id=str(uuid.uuid4()),
            project_id=project_id,
            category=MemoryCategory.CS_MISUNDERSTANDING,
            lesson_text="Klien sering salah nominal transfer. Ingatkan nominal PERSIS saat kirim invoice.",
            severity=MemorySeverity.MEDIUM,
            target_agent="CS",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        memories_to_save.append(memory)

    if final_state in ("CHURNED",):
        memory = CorporateMemory(
            memory_id=str(uuid.uuid4()),
            project_id=project_id,
            category=MemoryCategory.CLIENT_CHURN_REASON,
            lesson_text="Proyek gagal/churn. Evaluasi spesifikasi awal dan ekspektasi klien.",
            severity=MemorySeverity.HIGH,
            target_agent="MANAGER",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        memories_to_save.append(memory)

    for memory in memories_to_save:
        await save_corporate_memory(memory)

    return memories_to_save