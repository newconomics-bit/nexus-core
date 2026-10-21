import json
import os
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


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


async def call_llm(model: str, system_prompt: str, user_message: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return _mock_reply(user_message)

    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    content = completion.choices[0].message.content
    return content or ""
