import uuid
import json
from datetime import datetime, timezone
from typing import Optional

from database import (
    save_campaign,
    save_campaign_kpi,
    save_icp,
    save_battlecard,
    save_ab_test,
    save_lead,
    save_partnership,
    get_campaign,
)
from agents.text_quality_gate import enforce
from models import (
    Campaign,
    CampaignObjective,
    CampaignStatus,
    CampaignKPI,
    ICPDefinition,
    CompetitiveBattlecard,
    ABTest,
    ABTestStatus,
    LeadGenResult,
    PartnershipEvaluation,
    PartnerType,
    PartnershipStatus,
)


# 8-step campaign workflow steps
CAMPAIGN_STEPS = [
    "Define objectives",
    "Identify audience",
    "Develop strategy",
    "Create assets",
    "Plan execution",
    "Set measurement",
    "Launch",
    "Analyze",
]


async def plan_campaign(
    name: str,
    objective: CampaignObjective,
    target_audience: str,
    channels: list[str],
) -> Campaign:
    """Plan a campaign using 8-step workflow."""
    campaign_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    campaign = Campaign(
        campaign_id=campaign_id,
        name=name,
        objective=objective,
        target_audience=target_audience,
        channel_mix=channels,
        status=CampaignStatus.PLANNING,
        created_at=now,
    )

    await save_campaign(campaign)

    # Create default KPIs based on objective
    kpi_targets = {
        CampaignObjective.LEAD_GEN: [
            ("MQLs", 200.0),
            ("CPL", 50000.0),
            ("Conversion rate", 15.0),
        ],
        CampaignObjective.BRAND_AWARENESS: [
            ("Impressions", 100000.0),
            ("Reach", 50000.0),
            ("Engagement rate", 5.0),
        ],
        CampaignObjective.RETENTION: [
            ("NPS", 50.0),
            ("Churn rate", 5.0),
            ("Upsell rate", 20.0),
        ],
    }

    for metric_name, target_value in kpi_targets.get(objective, []):
        kpi = CampaignKPI(
            kpi_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            metric_name=metric_name,
            target_value=target_value,
            actual_value=0.0,
            measured_at=datetime.now(timezone.utc).isoformat(),
        )
        await save_campaign_kpi(kpi)

    return campaign


async def create_positioning(
    target_audience: str,
    alternatives: list[str],
    unique_attributes: list[str],
) -> dict:
    """Create positioning using April Dunford 6-step framework."""
    # Step 1: List competitive alternatives
    alternatives_str = ", ".join(alternatives)

    # Step 2: Isolate unique attributes
    unique_attrs_str = ", ".join(unique_attributes)

    # Step 3: Map attributes to value
    value_map = "\n".join([f"- {attr}: solves {attr.lower()} for {target_audience}" for attr in unique_attributes])

    # Step 4: Define best-fit customers
    best_fit = f"{target_audience} who need {', '.join(unique_attributes[:3])}"

    # Step 5: Nail market category
    market_category = "SaaS B2B untuk UMKM Indonesia"

    # Step 6: Layer trends
    trends = ["Digitalisasi UMKM", "Pembayaran QRIS", "Automasi akuntansi"]

    # Generate value proposition
    value_prop = (
        f"Untuk {target_audience}, "
        f"RakitDigital adalah {market_category} yang "
        f"{', '.join(unique_attributes[:2])}. "
        f"Berbeda dengan {alternatives_str}, kami {unique_attributes[0]}."
    )

    return {
        "value_prop": value_prop,
        "best_fit_customers": best_fit,
        "market_category": market_category,
        "trends": trends,
        "alternatives": alternatives_str,
        "unique_attributes": unique_attrs_str,
        "value_map": value_map,
    }


async def define_icp(
    business_type: str,
    firmographics: dict,
    technographics: dict,
    psychographics: dict,
    buyer_personas: list[str],
) -> ICPDefinition:
    """Define Ideal Customer Profile."""
    icp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    icp = ICPDefinition(
        icp_id=icp_id,
        business_type=business_type,
        firmographics=firmographics,
        technographics=technographics,
        psychographics=psychographics,
        buyer_personas=buyer_personas,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_icp(icp)
    return icp


async def create_battlecard(
    competitor_name: str,
    strengths: list[str],
    weaknesses: list[str],
    our_advantages: list[str],
    when_to_win: list[str],
    when_to_lose: list[str],
    talk_tracks: list[str],
) -> CompetitiveBattlecard:
    """Create competitive battlecard using ETIS framework."""
    battlecard_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    battlecard = CompetitiveBattlecard(
        battlecard_id=battlecard_id,
        competitor_name=competitor_name,
        strengths=strengths,
        weaknesses=weaknesses,
        our_advantages=our_advantages,
        when_to_win=when_to_win,
        when_to_lose=when_to_lose,
        talk_tracks=talk_tracks,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_battlecard(battlecard)
    return battlecard


async def design_ab_test(
    campaign_id: str,
    variant_a: str,
    variant_b: str,
    metric: str,
    sample_size_a: int,
    sample_size_b: int,
) -> ABTest:
    """Design an A/B test."""
    test_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Verify campaign exists
    campaign = await get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")

    test = ABTest(
        test_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        variant_a=variant_a,
        variant_b=variant_b,
        metric=metric,
        sample_size_a=sample_size_a,
        sample_size_b=sample_size_b,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_ab_test(test)
    return test


async def analyze_ab_test(test_id: str) -> ABTest:
    """Analyze A/B test results and determine winner."""
    from database import get_ab_test, save_ab_test

    test = await get_ab_test(test_id)
    if not test:
        raise ValueError(f"Test not found: {test_id}")

    if test.status == ABTestStatus.COMPLETED:
        return test

    # Calculate conversion rates
    conv_a = test.conversion_a / test.sample_size_a if test.sample_size_a > 0 else 0
    conv_b = test.conversion_b / test.sample_size_b if test.sample_size_b > 0 else 0

    diff = abs(conv_a - conv_b)
    significance_threshold = 0.05  # 5% difference for significance

    if diff < significance_threshold:
        test.winner = "TIE"
    elif conv_a > conv_b:
        test.winner = "A"
    else:
        test.winner = "B"

    test.status = ABTestStatus.COMPLETED
    await save_ab_test(test)

    return test


async def generate_leads_etis(niche: str, city: str, limit: int = 10) -> list[LeadGenResult]:
    """Generate leads ethically using mock data (mock for API resmi/direktori ber-izin)."""
    from database import save_lead

    # Mock data - in production, this would call API resmi (Google Places API, direktori ber-izin)
    mock_leads = [
        {
            "business_name": f"Toko {niche} Jaya",
            "contact_info": {"phone": "0812-3456-7890", "email": "toko.jaya@example.com"},
        },
        {
            "business_name": f"Warung {niche} Makmur",
            "contact_info": {"phone": "0813-9876-5432", "email": "warung.makmur@example.com"},
        },
        {
            "business_name": f"CV {niche} Sejahtera",
            "contact_info": {"phone": "0821-1111-2222", "email": "cv.sejahtera@example.com"},
        },
        {
            "business_name": f"UD {niche} Berkah",
            "contact_info": {"phone": "0857-3333-4444", "email": "ud.berkah@example.com"},
        },
        {
            "business_name": f"PT {niche} Maju",
            "contact_info": {"phone": "0878-5555-6666", "email": "pt.maju@example.com"},
        },
    ]

    leads = []
    for i in range(min(limit, len(mock_leads))):
        lead_data = mock_leads[i]
        lead = LeadGenResult(
            lead_id=str(uuid.uuid4()),
            source="mock_api_resmi",
            business_name=lead_data["business_name"],
            contact_info=lead_data["contact_info"],
            niche=niche,
            city=city,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        await save_lead(lead)
        leads.append(lead)

    return leads


async def evaluate_partnership(
    partner_name: str,
    partner_type: PartnerType,
    cost_score: int,
    reliability_score: int,
    support_score: int,
    integration_score: int,
) -> PartnershipEvaluation:
    """Evaluate partnership using scoring framework."""
    # Validate scores
    for score_name, score in [
        ("cost_score", cost_score),
        ("reliability_score", reliability_score),
        ("support_score", support_score),
        ("integration_score", integration_score),
    ]:
        if not 0 <= score <= 100:
            raise ValueError(f"{score_name} must be between 0 and 100")

    criteria_scores = {
        "cost": cost_score,
        "reliability": reliability_score,
        "support": support_score,
        "integration": integration_score,
    }

    total_score = (cost_score + reliability_score + support_score + integration_score) // 4

    if total_score >= 70:
        status = PartnershipStatus.RECOMMENDED
    else:
        status = PartnershipStatus.REJECTED

    evaluation = PartnershipEvaluation(
        partnership_id=str(uuid.uuid4()),
        partner_name=partner_name,
        partner_type=partner_type,
        criteria_scores=criteria_scores,
        total_score=total_score,
        status=status,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )

    await save_partnership(evaluation)
    return evaluation