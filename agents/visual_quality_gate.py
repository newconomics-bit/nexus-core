import re
from typing import Literal

# Patterns for visual quality gate (Hallmark/Impeccable inspired)

# Emoji used as icon (in button, heading, bullet)
EMOJI_AS_ICON_PATTERN = re.compile(
    r"(?:<button[^>]*>|<h[1-6][^>]*>|<li[^>]*>|<span[^>]*class=[\"'][^\"']*icon[^\"']*[\"'][^>]*>)[^<]*[🚀✨💡🔥💯🎯⭐🌟💪🙌👏🎉🚨⚡️💎🏆🥇][^<]*",
    re.IGNORECASE
)

# Purple gradient detection (Tailwind purple-500/600, raw CSS)
PURPLE_GRADIENT_PATTERNS = [
    re.compile(r"linear-gradient\([^)]*(?:#8b5cf6|#a855f7|#9333ea|#7c3aed|#6d28d9|purple-500|purple-600|violet-500|violet-600)[^)]*\)", re.IGNORECASE),
    re.compile(r"gradient-(?:to-)?(?:r|t|b|l|br|bl|tr|tl)-purple", re.IGNORECASE),
    re.compile(r"from-purple-\d+\s+to-purple-\d+", re.IGNORECASE),
    re.compile(r"bg-gradient-to-[a-z]+\s+from-purple-\d+\s+to-purple-\d+", re.IGNORECASE),
]

# Inter font hardcoded without fallback
INTER_HARDCODED_PATTERNS = [
    re.compile(r"font-family\s*:\s*[\"']?Inter[\"']?\s*(?:;|})", re.IGNORECASE),
    re.compile(r"font-family\s*:\s*[\"']?Inter[\"']?\s*,\s*(?:sans-serif|system-ui)", re.IGNORECASE),
    re.compile(r"class=[\"'][^\"']*font-inter[^\"']*[\"']", re.IGNORECASE),
]

# Card stack: multiple consecutive card divs
CARD_STACK_PATTERN = re.compile(
    r"(?:<div[^>]*class=[\"'][^\"']*card[^\"']*[\"'][^>]*>.*?</div>\s*){4,}",
    re.IGNORECASE | re.DOTALL
)

# Missing SVG icon: empty svg or manual path drawing
MISSING_SVG_ICON_PATTERNS = [
    re.compile(r"<svg[^>]*>\s*</svg>", re.IGNORECASE),
    re.compile(r"<svg[^>]*><path[^>]*d=[\"'][^\"']{100,}[\"'][^>]*></svg>", re.IGNORECASE),
]


def _find_emoji_as_icon(content: str) -> list[dict]:
    findings = []
    for match in EMOJI_AS_ICON_PATTERN.finditer(content):
        line_num = content[:match.start()].count("\n") + 1
        findings.append({
            "rule": "emoji_as_icon",
            "severity": "HIGH",
            "location": f"line {line_num}: {match.group()[:80]}...",
        })
    return findings


def _find_purple_gradient(content: str) -> list[dict]:
    findings = []
    for pattern in PURPLE_GRADIENT_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            findings.append({
                "rule": "purple_gradient",
                "severity": "HIGH",
                "location": f"line {line_num}: {match.group()[:80]}...",
            })
    return findings


def _find_inter_hardcoded(content: str) -> list[dict]:
    findings = []
    for pattern in INTER_HARDCODED_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            findings.append({
                "rule": "inter_hardcoded",
                "severity": "MEDIUM",
                "location": f"line {line_num}: {match.group()[:80]}...",
            })
    return findings


def _find_card_stack(content: str) -> list[dict]:
    findings = []
    for match in CARD_STACK_PATTERN.finditer(content):
        line_num = content[:match.start()].count("\n") + 1
        findings.append({
            "rule": "card_stack",
            "severity": "MEDIUM",
            "location": f"line {line_num}: {match.group()[:80]}...",
        })
    return findings


def _find_missing_svg_icon(content: str) -> list[dict]:
    findings = []
    for pattern in MISSING_SVG_ICON_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            findings.append({
                "rule": "missing_svg_icon",
                "severity": "LOW",
                "location": f"line {line_num}: {match.group()[:80]}...",
            })
    return findings


def audit_frontend(artifact_content: str) -> dict:
    """
    Audit frontend artifact content for visual quality issues.
    Returns: {"findings": [...], "passed": bool}
    """
    all_findings = []
    
    all_findings.extend(_find_emoji_as_icon(artifact_content))
    all_findings.extend(_find_purple_gradient(artifact_content))
    all_findings.extend(_find_inter_hardcoded(artifact_content))
    all_findings.extend(_find_card_stack(artifact_content))
    all_findings.extend(_find_missing_svg_icon(artifact_content))
    
    # Gate: 0 CRITICAL, 0 HIGH -> PASSED
    has_critical = any(f["severity"] == "CRITICAL" for f in all_findings)
    has_high = any(f["severity"] == "HIGH" for f in all_findings)
    
    passed = not (has_critical or has_high)
    
    return {
        "findings": all_findings,
        "passed": passed,
        "summary": {
            "total": len(all_findings),
            "critical": sum(1 for f in all_findings if f["severity"] == "CRITICAL"),
            "high": sum(1 for f in all_findings if f["severity"] == "HIGH"),
            "medium": sum(1 for f in all_findings if f["severity"] == "MEDIUM"),
            "low": sum(1 for f in all_findings if f["severity"] == "LOW"),
        }
    }


class VisualQualityGate:
    """Stateless visual quality gate - pure Python, read-only, no external deps."""
    
    @staticmethod
    def audit(artifact_content: str) -> dict:
        return audit_frontend(artifact_content)