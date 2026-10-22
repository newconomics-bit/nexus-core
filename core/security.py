import os
from fastapi import Request, HTTPException, Header, Depends
from typing import Optional


def get_api_key() -> str:
    return os.getenv("RAKIT_API_KEY", "dev-secret-key-change-in-production")


def get_telegram_webhook_secret() -> str:
    return os.getenv("TELEGRAM_WEBHOOK_SECRET", "dev-webhook-secret-change-in-production")


def get_founder_chat_id() -> str:
    return os.getenv("FOUNDER_TELEGRAM_CHAT_ID", "123456789")


async def verify_api_key(request: Request) -> None:
    if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
        return

    api_key = request.headers.get("X-API-Key")
    expected_key = get_api_key()

    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing API Key"
        )


async def verify_telegram_secret(
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
) -> None:
    expected_secret = get_telegram_webhook_secret()
    if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing Telegram Webhook Secret"
        )


async def verify_founder_identity(chat_id: int) -> None:
    founder_chat_id = get_founder_chat_id()
    if str(chat_id) != str(founder_chat_id):
        raise HTTPException(
            status_code=403,
            detail="Akses Ditolak. Anda bukan MUHAMMAD MUFTI ZAKA."
        )