from models import DecisionType


def needs_founder_approval(decision_type: DecisionType, impact_score: int, **kwargs) -> bool:
    """
    Hardcode rules for which decisions require Founder approval.
    Returns True if Founder approval is needed, False if Pak Arif can decide.
    """
    if decision_type == DecisionType.PRICING_CHANGE:
        percent_change = kwargs.get("percent_change", 0)
        return percent_change > 10
    
    if decision_type == DecisionType.FEATURE_REQUEST:
        rice_score = kwargs.get("rice_score", 0)
        return rice_score >= 50  # Accepted features need Founder approval
    
    if decision_type == DecisionType.PROMPT_UPDATE:
        is_major = kwargs.get("is_major", False)
        return is_major
    
    if decision_type == DecisionType.TECH_STACK_CHANGE:
        return True  # ALWAYS requires Founder approval
    
    if decision_type == DecisionType.PR_REVIEW:
        lines_changed = kwargs.get("lines_changed", 0)
        return lines_changed >= 100
    
    # Default: require approval for unknown types
    return True


def get_escalation_matrix() -> dict:
    """Return documentation of the escalation matrix for all decision types."""
    return {
        "PRICING_CHANGE": {
            "rule": "percent_change > 10% -> Founder approval required",
            "examples": [
                {"percent_change": 5, "needs_founder": False, "approver": "Pak Arif"},
                {"percent_change": 15, "needs_founder": True, "approver": "Founder"},
            ],
        },
        "FEATURE_REQUEST": {
            "rule": "RICE score >= 50 (ACCEPTED) -> Founder approval required",
            "examples": [
                {"rice_score": 30, "needs_founder": False, "approver": "Pak Arif (REJECTED)"},
                {"rice_score": 60, "needs_founder": True, "approver": "Founder"},
            ],
        },
        "PROMPT_UPDATE": {
            "rule": "Major change (section/jobdesk) -> Founder approval required",
            "examples": [
                {"is_major": False, "needs_founder": False, "approver": "Pak Arif"},
                {"is_major": True, "needs_founder": True, "approver": "Founder"},
            ],
        },
        "TECH_STACK_CHANGE": {
            "rule": "ALWAYS requires Founder approval",
            "examples": [
                {"needs_founder": True, "approver": "Founder"},
            ],
        },
        "PR_REVIEW": {
            "rule": "lines_changed >= 100 -> Founder approval required",
            "examples": [
                {"lines_changed": 50, "needs_founder": False, "approver": "Pak Arif"},
                {"lines_changed": 150, "needs_founder": True, "approver": "Founder"},
            ],
        },
    }