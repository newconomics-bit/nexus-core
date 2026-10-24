import re
from typing import Literal

# Banned phrases from ANTI_SLOP_RULES.md
BANNED_PHRASES = [
    "mari kita selami",
    "di era digital",
    "membuka potensi",
    "revolusioner",
    "game-changer",
    "cutting-edge",
    "ini bukan sekadar",
    "pada akhirnya",
    "kesimpulannya",
    "delve",
    "d.e.l.v.e",
    "unlock potential",
    "elevate",
    "transformasi",
    "paradigma",
    "ekosistem",
    "sinergi",
    "holistik",
    "end-to-end",
    "seamless",
    "best-in-class",
    "world-class",
    "state-of-the-art",
    "revolusi",
    "bangkit",
    "menjangkau",
    "memberdayakan",
]

# Emoji pattern for bullet/heading spam
EMOJI_PATTERN = re.compile(r"^[🚀✨💡🔥💯🎯⭐🌟💪🙌👏🎉🚨⚡️💎🏆🥇]\s", re.MULTILINE)

# Dramatic fragment: single sentence paragraph that's very short
DRAMATIC_FRAGMENT_PATTERN = re.compile(r"^\s*[A-Z][^.!?]{5,80}[.!?]\s*$", re.MULTILINE)

# Rule of three: exactly 3 bullet points in a list (detect common patterns)
BULLET_PATTERN = re.compile(r"^[\s]*[-*•]\s+.+$", re.MULTILINE)
EMOJI_BULLET_PATTERN = re.compile(r"^[🚀✨💡🔥💯🎯⭐🌟💪🙌👏🎉🚨⚡️💎🏆🥇]\s+.+$", re.MULTILINE)

# Opening fluff patterns
OPENING_FLUFF_PATTERNS = [
    r"^di era digital",
    r"^mari kita",
    r"^kami memahami bahwa",
    r"^penting untuk dicatat bahwa",
    r"^seperti yang kita ketahui",
    r"^dalam dunia yang",
    r"^ini bukan sekadar",
]


def _count_banned_phrases(text: str) -> int:
    text_lower = text.lower()
    count = 0
    for phrase in BANNED_PHRASES:
        count += text_lower.count(phrase.lower())
    return count


def _check_opening_fluff(text: str) -> bool:
    text_stripped = text.strip().lower()
    for pattern in OPENING_FLUFF_PATTERNS:
        if re.search(pattern, text_stripped):
            return True
    return False


def _check_rule_of_three(text: str) -> int:
    """Count bullet lists that have exactly 3 items (penalty if forced)"""
    lines = text.split("\n")
    in_list = False
    list_count = 0
    penalty = 0
    
    for line in lines:
        is_bullet = BULLET_PATTERN.match(line) or EMOJI_BULLET_PATTERN.match(line)
        if is_bullet:
            if not in_list:
                in_list = True
                list_count = 1
            else:
                list_count += 1
        else:
            if in_list:
                if list_count == 3:
                    penalty += 1
                in_list = False
                list_count = 0
    
    # Check last list
    if in_list and list_count == 3:
        penalty += 1
    
    return penalty


def _count_emoji_spam(text: str) -> int:
    return len(EMOJI_PATTERN.findall(text))


def _count_dramatic_fragments(text: str) -> int:
    """Count single-sentence paragraphs that look like dramatic fragments"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    count = 0
    for p in paragraphs:
        if DRAMATIC_FRAGMENT_PATTERN.match(p) and len(p) < 100:
            count += 1
    return count


def score_text(text: str) -> dict:
    """
    Score text 0-50 across 5 dimensions.
    Each dimension max 10 points.
    """
    banned_count = _count_banned_phrases(text)
    opening_fluff = _check_opening_fluff(text)
    rule_of_three_penalty = _check_rule_of_three(text)
    emoji_spam = _count_emoji_spam(text)
    dramatic_fragments = _count_dramatic_fragments(text)
    
    # Dimension scores (10 = perfect, 0 = worst)
    banned_score = max(0, 10 - banned_count * 3)
    opening_score = 0 if opening_fluff else 10
    rule_of_three_score = max(0, 10 - rule_of_three_penalty * 3)
    emoji_score = max(0, 10 - emoji_spam * 3)
    dramatic_score = max(0, 10 - dramatic_fragments * 5)
    
    total_score = banned_score + opening_score + rule_of_three_score + emoji_score + dramatic_score
    
    violations = []
    if banned_count > 0:
        violations.append(f"banned_phrases: {banned_count} occurrence(s)")
    if opening_fluff:
        violations.append("opening_fluff: detected")
    if rule_of_three_penalty > 0:
        violations.append(f"rule_of_three: {rule_of_three_penalty} forced 3-item list(s)")
    if emoji_spam > 0:
        violations.append(f"emoji_spam: {emoji_spam} emoji bullet(s)")
    if dramatic_fragments > 0:
        violations.append(f"dramatic_fragment: {dramatic_fragments} single-sentence paragraph(s)")
    
    return {
        "score": total_score,
        "passed": total_score >= 35,
        "violations": violations,
        "details": {
            "banned_phrases": banned_score,
            "opening_fluff": opening_score,
            "rule_of_three": rule_of_three_score,
            "emoji_spam": emoji_score,
            "dramatic_fragment": dramatic_score,
        }
    }


def enforce(text: str) -> tuple[bool, str]:
    """
    Returns (should_send, message).
    If should_send=False, message contains rewrite instruction.
    """
    result = score_text(text)
    if result["passed"]:
        return True, "OK"
    
    violation_str = "; ".join(result["violations"])
    msg = (
        f"Teks gagal Text Quality Gate (skor {result['score']}/50). "
        f"Violations: {violation_str}. "
        f"Tulis ulang tanpa frasa terlarang, emoji bullet, paragraf dramatis, dan rule-of-three paksa."
    )
    return False, msg


class TextQualityGate:
    """Stateless text quality gate - pure Python, no external deps."""
    
    @staticmethod
    def check(text: str) -> dict:
        return score_text(text)
    
    @staticmethod
    def enforce(text: str) -> tuple[bool, str]:
        return enforce(text)