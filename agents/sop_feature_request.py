import uuid
from datetime import datetime, timezone

from database import save_feature_request
from core.telegram_bot import send_message
from models import FeatureRequest, FeatureRequestStatus


IMPACT_VALUES = {
    "massive": 3,
    "high": 2,
    "medium": 1,
    "low": 0.5,
    "minimal": 0.25,
}

CONFIDENCE_VALUES = {
    "high": 100,
    "medium": 80,
    "low": 50,
}


def calculate_rice_score(reach: int, impact: str, confidence: str, effort: float) -> int:
    impact_val = IMPACT_VALUES.get(impact.lower(), 1)
    confidence_val = CONFIDENCE_VALUES.get(confidence.lower(), 80)
    score = (reach * impact_val * confidence_val) / effort
    return int(round(score))


async def evaluate_feature_request(
    description: str,
    reach: int,
    impact: str,
    confidence: str,
    effort: float,
    client_id: str | None = None,
) -> FeatureRequest:
    rice_score = calculate_rice_score(reach, impact, confidence, effort)

    if rice_score >= 50:
        status = FeatureRequestStatus.ACCEPTED
        roadmap_target = "Next Quarter"
        message = f"✅ Feature request ACCEPTED: {description} (RICE: {rice_score}, Target: {roadmap_target})"
        await send_message(message)
    else:
        status = FeatureRequestStatus.REJECTED
        roadmap_target = "Not planned"
        message = f"❌ Feature request REJECTED: {description} (RICE: {rice_score} < 50)"

    request = FeatureRequest(
        request_id=str(uuid.uuid4()),
        client_id=client_id,
        description=description,
        rice_score=rice_score,
        status=status,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        roadmap_target=roadmap_target,
    )

    await save_feature_request(request)
    return request