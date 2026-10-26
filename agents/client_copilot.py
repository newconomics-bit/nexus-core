"""
Client Co-Pilot Agent
AI Dashboard Insight Generator - receives structured JSON from Python, returns human-readable insight.
DOES NOT query database directly - data must be passed from endpoint.
"""
import json
from core.llm_gateway import call_llm

COPILOT_MODEL = "deepseek/deepseek-chat-v3-0324"  # Use primary model for insights


async def generate_business_insight(structured_data: dict) -> str:
    """
    Generate a business insight for the client dashboard.
    
    Args:
        structured_data: Dict with keys like:
            - date: str (e.g., "Hari Ini")
            - margin: int (margin in IDR)
            - anomaly: str (optional, e.g., "Diskon meja 4 terlalu besar")
            - void_count: int (optional)
            - revenue: int (optional)
            - top_items: list[dict] (optional)
            - low_stock: list[str] (optional)
    
    Returns:
        str: One professional, concise sentence in Indonesian "tongkrongan bisnis" style.
    """
    # Build prompt from structured data
    prompt = _build_copilot_prompt(structured_data)
    
    system_prompt = (
        "Kamu adalah AI Co-Pilot di dashboard owner UMKM. "
        "Tugasmu: buat 1 kalimat singkat, sopan, profesional untuk owner bisnis "
        "berdasarkan data JSON yang diberikan. "
        "ATURAN WAJIB:\n"
        "1. JANGAN mengarang angka - hanya gunakan data yang diberikan.\n"
        "2. Bahasa Indonesia 'tongkrongan bisnis': pakai 'Bang/Kak', jujur, realistis.\n"
        "3. Maksimal 1 kalimat (bisa panjang tapi 1 titik saja).\n"
        "4. Fokus pada actionable insight, bukan deskripsi data mentah.\n"
        "5. Jika margin negatif/anomali -> peringatan sopan + saran.\n"
        "6. Jika normal -> motivasi ringan + highlight poin baik.\n"
        "7. DILARANG: emoji berlebihan, frasa slop (delve, unlock potential, dll), "
        "paragraf dramatis 1 kalimat."
    )
    
    try:
        insight = await call_llm("deepseek/deepseek-chat-v3-0324", system_prompt, prompt)
        # Apply text quality gate
        from agents.text_quality_gate import enforce
        should_send, msg = enforce(insight)
        if should_send:
            return insight
        else:
            # Fallback if quality gate fails
            return _fallback_insight(structured_data)
    except Exception as e:
        print(f"[Co-Pilot] LLM failed: {e}")
        return _fallback_insight(structured_data)


def _build_copilot_prompt(data: dict) -> str:
    """Build prompt from structured data."""
    parts = ["Data hari ini:"]
    
    if "date" in data:
        parts.append(f"- Tanggal: {data['date']}")
    if "margin" in data:
        parts.append(f"- Margin: Rp {data['margin']:,}")
    if "revenue" in data:
        parts.append(f"- Revenue: Rp {data['revenue']:,}")
    if "anomaly" in data and data["anomaly"]:
        parts.append(f"- Anomali: {data['anomaly']}")
    if "void_count" in data:
        parts.append(f"- Void/Pembatalan: {data['void_count']}x")
    if "top_items" in data and data["top_items"]:
        items = ", ".join([f"{i.get('name', '')} (Rp {i.get('margin', 0):,})" for i in data["top_items"][:3]])
        parts.append(f"- Top margin: {items}")
    if "low_stock" in data and data["low_stock"]:
        parts.append(f"- Stok rendah: {', '.join(data['low_stock'][:3])}")
    
    parts.append("\nBuat 1 kalimat insight untuk owner.")
    return "\n".join(parts)


def _fallback_insight(data: dict) -> str:
    """Deterministic fallback insight when LLM fails."""
    margin = data.get("margin", 0)
    anomaly = data.get("anomaly", "")
    void_count = data.get("void_count", 0)
    
    if margin < 0:
        return f"Bang, margin hari ini minus Rp {abs(margin):,}{', ' + anomaly if anomaly else ''} — cek diskon & void yang {void_count}x, biar besok balik positif."
    elif margin < 100_000:
        return f"Bang, margin tipis Rp {margin:,}{', ' + anomaly if anomaly else ''} — pertimbangkan naikkan harga item top atau kurangi diskon."
    else:
        return f"Bang, margin solid Rp {margin:,} hari ini{', ' + anomaly if anomaly else ''} — lanjutkan, tapi awasi void {void_count}x biar gak bocor."