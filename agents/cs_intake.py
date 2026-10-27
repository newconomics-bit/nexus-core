import re
from pathlib import Path
from datetime import datetime, timezone
import uuid

from pydantic import ValidationError

from agents.text_quality_gate import enforce
from core.llm_gateway import call_llm
from core.pii_masker import mask_pii_in_text
from core.consultation_matrix import (
    detect_business_type,
    is_enterprise_request,
    generate_consultative_response,
    get_recommended_config,
)
from core.curriculum import CURRICULUM_SOURCES
from database import (
    save_custom_request,
    search_patterns,
    create_learning_task,
)
from models import ProjectSpec, CustomRequest, CustomRequestStatus, LearningTask, LearningTaskStatus

SARI_MODEL = "anthropic/claude-3.5-sonnet"
_ANTI_SLOP_PATH = Path(__file__).resolve().parents[1] / "ANTI_SLOP_RULES.md"
ANTI_SLOP_RULES = _ANTI_SLOP_PATH.read_text(encoding="utf-8")
_JSON_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

# Prompt injection protection patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all)\s+instructions?",
    r"forget\s+(everything|previous|above)",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"pretend\s+to\s+be",
    r"roleplay\s+as",
    r"output\s+(the\s+)?(system\s+)?prompt",
    r"show\s+me\s+(the\s+)?(api\s+)?keys?",
    r"reveal\s+(secrets?|passwords?)",
    r"bypass\s+(security|auth)",
    r"admin\s+mode",
    r"developer\s+mode",
]
_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def _detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attempts in client messages."""
    if _INJECTION_REGEX.search(text):
        return True
    # Also check for excessive length (potential context stuffing)
    if len(text) > 5000:
        return True
    return False


def _handle_enterprise_request(project_id: str, client_message: str) -> dict:
    """Handle RAKIT-CUSTOM / enterprise requests."""
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    custom_request = CustomRequest(
        request_id=request_id,
        client_name="Unknown",  # Will be updated when client provides name
        description=client_message,
        status=CustomRequestStatus.PENDING_REVIEW,
        estimated_budget=15_000_000,
        created_at=now,
    )
    
    # Save to database (fire and forget - don't await in mock)
    import asyncio
    asyncio.create_task(save_custom_request(custom_request))
    
    return {
        "status": "CUSTOM_REQUEST_CREATED",
        "reply": (
            "Kode terverifikasi. Permintaan Anda diprioritaskan. "
            "Tim Arsitek kami akan melakukan Feasibility Study 1x24 jam. "
            "Estimasi awal mulai Rp 15.000.000. Setuju untuk diskusi teknis?"
        ),
        "custom_request_id": request_id,
    }


async def _handle_standard_business(project_id: str, client_message: str) -> dict:
    """Handle standard business types with consultative response + pattern search."""
    business_type = detect_business_type(client_message)
    
    # Search for relevant patterns based on client message
    patterns = []
    try:
        patterns = await search_patterns(client_message, top_k=1)
    except Exception:
        patterns = []
    
    if business_type:
        response = generate_consultative_response(business_type)
        if response["recognized"]:
            # Enhance with pattern match if found
            pattern_info = ""
            if patterns:
                p = patterns[0]
                hidden_feats = list(p.features.keys())[:3]
                pattern_info = (
                    f"\n\nKami sudah memahami pola sistem seperti {p.reference_company}. "
                    f"Biasanya butuh integrasi {', '.join(hidden_feats)}. "
                    f"Estimasi build: {p.estimated_build_hours} jam. "
                    f"Kakak mau sekalian kami bikinkan custom dengan value yang jelas?"
                )
            
            return {
                "status": "CONSULTATIVE_RESPONSE",
                "reply": response["consultative_message"] + pattern_info,
                "business_type": business_type,
                "recommended_config": get_recommended_config(business_type),
                "matched_pattern": patterns[0].pattern_id if patterns else None,
            }
    
    # If no business type detected but client mentions a reference (kayak X, seperti X, mirip X)
    reference_keywords = ["kayak", "seperti", "mirip", "referensi", "contoh"]
    if any(kw in client_message.lower() for kw in reference_keywords):
        # Create learning task for unknown reference
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        learning_task = LearningTask(
            task_id=task_id,
            target_url="",  # No URL yet, just reference
            business_type="unknown",
            reference_company=client_message[:100],
            status=LearningTaskStatus.PENDING,
            created_at=now,
        )
        try:
            await create_learning_task(learning_task)
        except Exception:
            pass  # Silent fail for learning task creation
        
        return {
            "status": "LEARNING_TASK_CREATED",
            "reply": (
                "Catatan khusus kami terima. Tim riset kami akan mempelajari pola tersebut "
                "dan kembali dengan penawaran lengkap dalam 1x24 jam."
            ),
            "learning_task_id": task_id,
        }
    
    return {"status": "NEED_MORE_INFO", "reply": "Halo Bang, bisnisnya apa ya? (cafe/salon/retail/distributor/restoran)"}


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
    
    # Check for RAKIT-CUSTOM / enterprise request FIRST
    if is_enterprise_request(client_message):
        return _handle_enterprise_request(project_id, client_message)
    
    # Check for standard business types (consultative response)
    standard_response = await _handle_standard_business(project_id, client_message)
    if standard_response["status"] in ("CONSULTATIVE_RESPONSE", "LEARNING_TASK_CREATED"):
        return standard_response
    
    # Fallback to LLM-based discovery for SPEC completion
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
