import uuid
from datetime import datetime, timezone
from pathlib import Path

from database import save_technical_decision, save_corporate_memory
from core.telegram_bot import send_approval_card, send_message
from models import (
    TechnicalDecision,
    DecisionType,
    DecisionStatus,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    CorporateMemory,
    MemoryCategory,
    MemorySeverity,
)


def evaluate_prompt_update(agent_name: str, proposed_changes: str) -> dict:
    """Evaluate if prompt update is major or minor."""
    proposed_lower = proposed_changes.lower()
    
    major_keywords = ["tambah section", "hapus section", "ubah jobdesk", "ganti tujuan", "ganti batasan"]
    is_major = any(keyword in proposed_lower for keyword in major_keywords)
    
    if is_major:
        return {
            "requires_approval": True,
            "reason": "Major prompt update (section/jobdesk change) requires Founder approval",
        }
    return {
        "requires_approval": False,
        "reason": "Minor prompt update (typo/clarification), Pak Arif can approve",
    }


async def process_prompt_update(
    agent_name: str,
    proposed_changes: str,
    decided_by: str = "pak_arif",
) -> TechnicalDecision:
    evaluation = evaluate_prompt_update(agent_name, proposed_changes)

    decision = TechnicalDecision(
        decision_id=str(uuid.uuid4()),
        decision_type=DecisionType.PROMPT_UPDATE,
        description=f"Prompt update for {agent_name}: {proposed_changes[:100]}",
        impact_score=80 if evaluation["requires_approval"] else 20,
        requires_founder_approval=evaluation["requires_approval"],
        decided_by=decided_by,
        decided_at=datetime.now(timezone.utc).isoformat(),
        status=DecisionStatus.PENDING if evaluation["requires_approval"] else DecisionStatus.APPROVED,
    )

    await save_technical_decision(decision)

    if evaluation["requires_approval"]:
        approval = ApprovalRequest(
            approval_id=str(uuid.uuid4()),
            project_id="",
            quote_id="",
            type=ApprovalType.PROMPT_UPDATE,
            payload={
                "agent_name": agent_name,
                "proposed_changes": proposed_changes,
                "decision_id": decision.decision_id,
            },
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_approval
        await save_approval(approval)
        await send_approval_card(approval)
    else:
        # Apply the update
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / f"{agent_name.lower()}.md"
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8")
            # Simple append for demo - in real impl would do proper patch
            content += f"\n\n<!-- Update by {decided_by} at {datetime.now(timezone.utc).isoformat()}: {proposed_changes} -->"
            prompt_path.write_text(content, encoding="utf-8")
        
        decision.status = DecisionStatus.APPROVED
        from database import save_technical_decision as save_td
        await save_td(decision)
        
        # Log to corporate memory
        memory = CorporateMemory(
            memory_id=str(uuid.uuid4()),
            project_id="",
            category=MemoryCategory.FINANCE_MARGIN_LEAK,
            lesson_text=f"Prompt updated for {agent_name}: {proposed_changes[:100]}",
            severity=MemorySeverity.LOW,
            target_agent="MANAGER",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_corporate_memory
        await save_corporate_memory(memory)
        
        await send_message(f"✅ Prompt update applied for {agent_name}: {proposed_changes}")

    return decision