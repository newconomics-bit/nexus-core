import os
import json
import httpx
from dotenv import load_dotenv

from models import ApprovalRequest

load_dotenv()


async def send_approval_card(approval: ApprovalRequest) -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("TELEGRAM MOCK MODE ACTIVE")
        print(f"MOCK APPROVAL CARD:")
        print(f"  Approval ID: {approval.approval_id}")
        print(f"  Type: {approval.type.value}")
        print(f"  Payload: {json.dumps(approval.payload, indent=2)}")
        return f"mock_{approval.approval_id}"

    text_parts = [
        "🔔 *Approval Request - RakitDigital*",
        f"🆔 *Approval ID:* `{approval.approval_id}`",
        f"📋 *Type:* {approval.type.value}",
    ]

    if approval.type.value == "DISCOUNT_ESCALATION":
        text_parts.extend([
            f"💰 *Discount:* {approval.payload.get('discount_pct', 0)}%",
            f"💵 *Harga Sebelum:* Rp {approval.payload.get('final_price_before', 0):,}".replace(",", "."),
            f"💵 *Harga Sesudah:* Rp {approval.payload.get('final_price_after', 0):,}".replace(",", "."),
        ])
    elif approval.type.value == "DEPLOY_PRODUCTION":
        text_parts.extend([
            f"🚀 *Deploy to Production*",
            f"🌐 *Domain:* {approval.payload.get('domain_choice', 'N/A')}",
            f"🔗 *URL:* {approval.payload.get('hosted_url') or approval.payload.get('custom_domain_url') or 'N/A'}",
        ])
    elif approval.type.value == "QA_ESCALATION":
        text_parts.extend([
            f"⚠️ *QA Escalation*",
            f"🔄 *Cycle:* {approval.payload.get('cycle', 0)}",
            f"🔴 *Critical:* {approval.payload.get('critical_findings', 0)}",
            f"🟠 *High:* {approval.payload.get('high_findings', 0)}",
            f"📝 *Message:* {approval.payload.get('message', 'N/A')}",
        ])

    text = "\n".join(text_parts)

    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Approve",
                    "callback_data": f"APPROVE|{approval.approval_id}",
                },
                {
                    "text": "❌ Reject",
                    "callback_data": f"REJECT|{approval.approval_id}",
                },
            ]
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": reply_markup,
                    "parse_mode": "Markdown",
                },
            )
            response.raise_for_status()
            return str(response.json()["result"]["message_id"])
    except Exception as e:
        print(f"TELEGRAM ERROR: {e}")
        raise


async def send_access_denied_message(chat_id: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM MOCK MODE: Access denied message would be sent")
        return

    text = (
        "⛔ *AKSES DITOLAK*\n\n"
        "Anda bukan MUHAMMAD MUFTI ZAKA.\n"
        "Hanya Founder yang berhak menyetujui approval ini."
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as e:
        print(f"TELEGRAM ERROR sending access denied: {e}")