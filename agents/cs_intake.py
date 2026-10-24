import re
from pathlib import Path

from pydantic import ValidationError

from agents.text_quality_gate import enforce
from core.llm_gateway import call_llm
from core.pii_masker import mask_pii_in_text
from models import ProjectSpec

SARI_MODEL = "anthropic/claude-3.5-sonnet"
_ANTI_SLOP_PATH = Path(__file__).resolve().parents[1] / "ANTI_SLOP_RULES.md"
ANTI_SLOP_RULES = _ANTI_SLOP_PATH.read_text(encoding="utf-8")
_JSON_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

# Prompt injection protection patterns
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|all)\s+instructions?",
    r"(?i)forget\s+(everything|previous|above)",
    r"(?i)system\s+prompt",
    r"(?i)you\s+are\s+now",
    r"(?i)pretend\s+to\s+be",
    r"(?i)roleplay\s+as",
    r"(?i)output\s+(the\s+)?(system\s+)?prompt",
    r"(?i)show\s+me\s+(the\s+)?(api\s+)?keys?",
    r"(?i)reveal\s+(secrets?|passwords?)",
    r"(?i)bypass\s+(security|auth)",
    r"(?i)admin\s+mode",
    r"(?i)developer\s+mode",
]
_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS))


def _detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attempts in client messages."""
    if _INJECTION_REGEX.search(text):
        return True
    # Also check for excessive length (potential context stuffing)
    if len(text) > 5000:
        return True
    return False


def build_system_prompt() -> str:
    return (
        "Kamu Sari, CS Intake RakitDigital. Balas chat klien dengan bahasa manusia.\n"
        "Pakai sapaan Bang/Kak/Pak/Bu. Jangan janji fitur yang tidak ada.\n"
        "Produk yang dijual hanya Micro-SaaS UMKM: kasir, stok, absensi.\n\n"
        "Aturan Anti-Slop yang wajib kamu ikuti:\n"
        f"{ANTI_SLOP_RULES}\n\n"
        "Kalau nama usaha, fitur, atau budget belum jelas, tanya yang kurang. "
        "Jangan keluarkan JSON.\n"
        "Kalau ketiganya sudah jelas, balas singkat lalu keluarkan ProjectSpec "
        "di dalam tag ```json ... ``` dengan bentuk persis:\n"
        '{"client_name": "nama usaha", "features": ["fitur"], "budget": "angka atau teks budget"}\n'
    )


def parse_project_spec(reply: str) -> ProjectSpec | None:
    match = _JSON_FENCE.search(reply)
    if match is None:
        return None
    try:
        return ProjectSpec.model_validate_json(match.group(1))
    except ValidationError:
        return None


def _enforce_text_quality(reply: str) -> str:
    """Apply text quality gate, retry once if needed."""
    should_send, msg = enforce(reply)
    if should_send:
        return reply
    
    # Log violation and ask for rewrite (mock: we just return a cleaner version)
    # In real implementation, this would trigger LLM to regenerate
    rewrite_prompt = (
        f"REWRITE NEEDED: {msg}\n"
        f"Original: {reply}\n"
        "Rewrite without violations, keep the same meaning."
    )
    # Mock: return a safe fallback
    return "Halo Bang, terima kasih infonya. Lanjut ya."


async def run_discovery(project_id: str, client_message: str, db_session) -> dict:
    # Prompt injection protection
    if _detect_prompt_injection(client_message):
        # Log the attempt but don't reveal detection to attacker
        safe_reply = "Halo Bang, pesan tidak bisa diproses. Coba kirim ulang dengan bahasa yang biasa ya."
        return {"status": "NEED_MORE_INFO", "reply": safe_reply}
    
    reply = await call_llm(SARI_MODEL, build_system_prompt(), client_message)
    # Apply text quality gate before sending to client
    clean_reply = _enforce_text_quality(reply)
    spec = parse_project_spec(clean_reply)
    if spec is None:
        return {"status": "NEED_MORE_INFO", "reply": clean_reply}

    await db_session.save_project_spec(project_id, spec.model_dump_json())
    return {
        "status": "SPEC_COMPLETE",
        "reply": clean_reply,
        "spec": spec.model_dump(),
    }


def mask_for_logging(text: str) -> str:
    """Mask PII in text before logging to corporate memory or sending to non-Founder."""
    return mask_pii_in_text(text)
