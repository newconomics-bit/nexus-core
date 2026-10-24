import uuid
from datetime import datetime, timezone

from database import save_technical_decision
from core.telegram_bot import send_approval_card
from models import (
    TechnicalDecision,
    DecisionType,
    DecisionStatus,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
)


async def evaluate_pricing_change(current_price: int, proposed_price: int) -> dict:
    percent_change = abs(proposed_price - current_price) / current_price * 100
    if percent_change > 10:
        return {
            "requires_approval": True,
            "reason": f"Pricing change {percent_change:.1f}% > 10% requires Founder approval",
            "percent_change": percent_change,
        }
    return {
        "requires_approval": False,
        "reason": f"Pricing change {percent_change:.1f}% <= 10%, Pak Arif can approve",
        "percent_change": percent_change,
    }


async def process_pricing_change(
    current_price: int, proposed_price: int, decided_by: str = "pak_arif"
) -> TechnicalDecision:
    evaluation = await evaluate_pricing_change(current_price, proposed_price)
    percent_change = evaluation["percent_change"]

    decision = TechnicalDecision(
        decision_id=str(uuid.uuid4()),
        decision_type=DecisionType.PRICING_CHANGE,
        description=f"Pricing change from Rp {current_price:,} to Rp {proposed_price:,} ({percent_change:.1f}%)",
        impact_score=int(percent_change * 2),  # Scale impact
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
            type=ApprovalType.PRICING_CHANGE,
            payload={
                "current_price": current_price,
                "proposed_price": proposed_price,
                "percent_change": percent_change,
                "decision_id": decision.decision_id,
            },
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        from database import save_approval
        await save_approval(approval)
        await send_approval_card(approval)
    else:
        decision.status = DecisionStatus.APPROVED
        from database import save_technical_decision as save_td
        await save_td(decision)

    return decision