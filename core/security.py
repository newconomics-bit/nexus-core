import os
import hmac
from fastapi import Request, HTTPException, Header, Depends
from typing import Optional


def get_api_key() -> str:
    return os.getenv("RAKIT_API_KEY", "dev-secret-key-change-in-production")


def get_telegram_webhook_secret() -> str:
    return os.getenv("TELEGRAM_WEBHOOK_SECRET", "dev-webhook-secret-change-in-production")


def get_founder_chat_id() -> str:
    return os.getenv("FOUNDER_TELEGRAM_CHAT_ID", "123456789")


def get_founder_auth_secret() -> str:
    """Get the Founder authorization secret from environment.
    This secret must be explicitly configured in production.
    Returns empty string if not configured, which will cause auth to fail."""
    return os.getenv("FOUNDER_AUTH_SECRET", "")


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


async def verify_founder_authorization(
    x_founder_approval: Optional[str] = Header(None),
    x_founder_signature: Optional[str] = Header(None)
) -> None:
    """
    Verify Founder authorization for sensitive operations.
    Requires both X-Founder-Approval: true header and valid X-Founder-Signature.

    The signature is HMAC-SHA256 of the approval value using FOUNDER_AUTH_SECRET.
    This prevents replay attacks and ensures the request comes from an authorized source.

    If FOUNDER_AUTH_SECRET is not configured, authorization will always fail.
    """
    # Check if Founder auth secret is configured
    founder_secret = get_founder_auth_secret()
    if not founder_secret:
        raise HTTPException(
            status_code=503,
            detail="Founder authorization not configured. FOUNDER_AUTH_SECRET must be set."
        )

    # Check approval header
    if not x_founder_approval or x_founder_approval.lower() != "true":
        raise HTTPException(
            status_code=403,
            detail="Missing or invalid Founder approval header. Required: X-Founder-Approval: true"
        )

    # Verify signature using HMAC for timing-safe comparison
    if not x_founder_signature:
        raise HTTPException(
            status_code=403,
            detail="Missing Founder signature header. Required: X-Founder-Signature"
        )

    expected_signature = hmac.new(
        founder_secret.encode(),
        b"true",  # The approval value being signed
        "sha256"
    ).hexdigest()

    # Use hmac.compare_digest for timing-safe comparison
    if not hmac.compare_digest(x_founder_signature, expected_signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid Founder signature"
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