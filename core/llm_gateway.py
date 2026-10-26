import json
import os
import re
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# LLM Configuration
PRIMARY_MODEL = "deepseek/deepseek-chat-v3-0324"  # DeepSeek V3 (cheap)
BACKUP_MODEL = "qwen/qwen-2.5-72b-instruct"  # Qwen backup via OpenRouter
GROQ_BASE_URL = "https://api.groq.com/openai/v1"  # Groq for Qwen backup

# Circuit breaker for LLM calls
_circuit_breaker_state = {
    "failures": 0,
    "open_until": 0,
    "failure_threshold": 3,
    "reset_timeout": 60,  # seconds
}
_circuit_breaker_lock = asyncio.Lock()


async def _check_circuit_breaker():
    """Check and update circuit breaker state. Returns True if calls allowed."""
    async with _circuit_breaker_lock:
        now = asyncio.get_event_loop().time()
        if _circuit_breaker_state["open_until"] > now:
            # Circuit is open, check if reset timeout has passed
            if now >= _circuit_breaker_state["open_until"]:
                # Reset circuit
                _circuit_breaker_state["failures"] = 0
                _circuit_breaker_state["open_until"] = 0
            else:
                return False  # Circuit open, calls blocked
        return True  # Circuit closed, calls allowed


def _record_failure():
    """Record a failure and potentially open the circuit."""
    _circuit_breaker_state["failures"] += 1
    if _circuit_breaker_state["failures"] >= _circuit_breaker_state["failure_threshold"]:
        _circuit_breaker_state["open_until"] = asyncio.get_event_loop().time() + _circuit_breaker_state["reset_timeout"]


def _record_success():
    """Record a success and reset failure count."""
    _circuit_breaker_state["failures"] = 0
    _circuit_breaker_state["open_until"] = 0


def _mock_reply(user_message: str) -> str:
    print("MOCK MODE ACTIVE")
    lowered = user_message.lower()
    if not all(token in lowered for token in ("nama", "fitur", "budget")):
        return (
            "Halo Bang, saya Sari dari RakitDigital. "
            "Mau dibuatkan apa? Saya butuh nama usaha, daftar fitur, dan budget-nya dulu."
        )

    nama = "Klien"
    fitur = ["kasir"]
    budget = "0"
    nama_match = re.search(r"nama(?:\s+usaha)?\s*[:\-]\s*([^.\n]+)", user_message, re.I)
    fitur_match = re.search(r"fitur\s*[:\-]\s*([^.\n]+)", user_message, re.I)
    budget_match = re.search(r"budget\s*[:\-]\s*([^\n.]+)", user_message, re.I)
    if nama_match:
        nama = nama_match.group(1).strip()
    if fitur_match:
        fitur = [
            part.strip()
            for part in re.split(r",|\sdan\s", fitur_match.group(1))
            if part.strip()
        ]
    if budget_match:
        budget = budget_match.group(1).strip()

    payload = json.dumps(
        {"client_name": nama, "features": fitur, "budget": budget},
        ensure_ascii=False,
    )
    return f"Oke Bang, saya catat requirement-nya.\n```json\n{payload}\n```"


async def _call_openrouter(model: str, system_prompt: str, user_message: str) -> str:
    """Call OpenRouter API with given model."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        result = _mock_reply(user_message)
        _record_success()
        return result

    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        content = completion.choices[0].message.content
        _record_success()
        return content or ""
    except Exception as e:
        _record_failure()
        raise


async def _call_groq(model: str, system_prompt: str, user_message: str) -> str:
    """Call Groq API with given model (for Qwen backup)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        result = _mock_reply(user_message)
        _record_success()
        return result

    client = AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        content = completion.choices[0].message.content
        _record_success()
        return content or ""
    except Exception as e:
        _record_failure()
        raise


async def call_llm(model: str, system_prompt: str, user_message: str) -> str:
    """
    Multi-LLM Fallback Gateway:
    1. Try Primary (DeepSeek V3 via OpenRouter)
    2. On failure (rate limit, timeout, API error), fallback to Backup (Qwen via Groq)
    """
    # Check circuit breaker
    if not await _check_circuit_breaker():
        raise Exception("Circuit breaker open - too many failures")
    
    # Primary: DeepSeek V3
    try:
        print(f"[LLM] Calling primary model: {PRIMARY_MODEL}")
        result = await _call_openrouter(PRIMARY_MODEL, system_prompt, user_message)
        print(f"[LLM] Primary succeeded")
        return result
    except Exception as e:
        print(f"[LLM] Primary failed: {e}. Switching to backup...")
        
        # Fallback: Qwen via Groq
        try:
            print(f"[LLM] Calling backup model: {BACKUP_MODEL} via Groq")
            result = await _call_groq(BACKUP_MODEL, system_prompt, user_message)
            print(f"[LLM] Backup succeeded")
            return result
        except Exception as e2:
            print(f"[LLM] Backup also failed: {e2}")
            _record_failure()
            raise Exception(f"Both primary and backup LLM failed: {e2}")
