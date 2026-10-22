import math
import uuid
from datetime import datetime, timezone

from database import get_latest_quote
from models import EffortEstimate, HppBreakdown, ProjectSpec, Quote, QuoteStatus

INFRA_COST = 150_000
LABOR_RATE = 75_000
DEFAULT_MARGIN_PCT = 75
PRICE_STEP = 50_000
QRIS_MDR_PCT = 0.007


class EscalationRequired(Exception):
    pass


class DiscountHardCap(Exception):
    pass


def ceil_to_50000(amount: float) -> int:
    return int(math.ceil(amount / PRICE_STEP) * PRICE_STEP)


def ceil_to_1000(amount: float) -> int:
    return int(math.ceil(amount / 1000) * 1000)


def selling_price(total_hpp: int, margin_pct: float, discount_pct: float) -> int:
    gross = ceil_to_50000(total_hpp * (100 + margin_pct) / 100)
    return int(round(gross * (100 - discount_pct) / 100))


def estimate_effort(spec: ProjectSpec) -> EffortEstimate:
    feature_count = len(spec.features)
    labor_hours = float(8 + 4 * feature_count)
    if feature_count <= 3:
        difficulty = "LOW"
    elif feature_count <= 6:
        difficulty = "MEDIUM"
    else:
        difficulty = "HIGH"
    return EffortEstimate(
        labor_hours=labor_hours,
        difficulty=difficulty,
        notes=f"Estimasi deterministik: {feature_count} fitur, {labor_hours:g} jam.",
    )


async def calculate_quote(
    project_id: str, spec: ProjectSpec, effort: EffortEstimate
) -> Quote:
    del spec
    latest = await get_latest_quote(project_id)
    version = 1 if latest is None else latest.version + 1
    labor_cost = int(round(effort.labor_hours * LABOR_RATE))
    qris_mdr = ceil_to_1000((INFRA_COST + labor_cost) * QRIS_MDR_PCT)
    total_hpp = INFRA_COST + labor_cost + qris_mdr
    final_price = selling_price(total_hpp, DEFAULT_MARGIN_PCT, 0)
    return Quote(
        quote_id=str(uuid.uuid4()),
        project_id=project_id,
        version=version,
        hpp_breakdown=HppBreakdown(
            infra_cost=INFRA_COST,
            labor_hours=effort.labor_hours,
            labor_rate=LABOR_RATE,
            qris_mdr=qris_mdr,
            total_hpp=total_hpp,
        ),
        margin_pct=DEFAULT_MARGIN_PCT,
        discount_pct=0,
        final_price=final_price,
        status=QuoteStatus.ACTIVE,
        valid_until_days=7,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def apply_discount(quote: Quote, discount_pct: int, founder_approved: bool) -> Quote:
    if discount_pct > 30:
        raise DiscountHardCap()
    if discount_pct > 10 and not founder_approved:
        raise EscalationRequired()
    final_price = selling_price(
        quote.hpp_breakdown.total_hpp, quote.margin_pct, discount_pct
    )
    return quote.model_copy(
        update={"discount_pct": discount_pct, "final_price": final_price}
    )
