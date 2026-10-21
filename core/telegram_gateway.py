import os

import httpx
from dotenv import load_dotenv

from models import ApprovalRequest

load_dotenv()


async def send_approval_request(approval: ApprovalRequest) -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM MOCK MODE ACTIVE")
        return f"mock_{approval.approval_id}"

    text = (
        "Approval RakitDigital\n"
        f"Project: {approval.project_id}\n"
        f"Tipe: {approval.type.value}\n"
        f"Diskon: {approval.payload.discount_pct}%\n"
        f"Harga sebelum: {approval.payload.final_price_before}\n"
        f"Harga sesudah: {approval.payload.final_price_after}"
    )
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "Approve",
                    "callback_data": f"APPROVED|{approval.approval_id}",
                },
                {
                    "text": "Reject",
                    "callback_data": f"REJECTED|{approval.approval_id}",
                },
            ]
        ]
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup},
        )
        response.raise_for_status()
        return str(response.json()["result"]["message_id"])
