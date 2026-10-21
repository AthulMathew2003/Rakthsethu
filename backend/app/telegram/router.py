import hmac
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.response import ApiResponse, success_response
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.telegram.client import TelegramClient
from app.telegram.handlers import TelegramHandler
from app.telegram.schemas import TelegramUpdate

logger = logging.getLogger("rakthasethu.telegram.router")

security_bearer = HTTPBearer(auto_error=False)


async def require_admin_or_secret(
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    session: AsyncSession = Depends(get_db),
) -> bool:
    """
    Allows access either via the matching 256-bit Telegram webhook secret header
    or via an authenticated SUPER_ADMIN user session.
    """
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
    if expected_secret and x_telegram_bot_api_secret_token and hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected_secret
    ):
        return True

    if auth and auth.credentials:
        try:
            payload = decode_access_token(auth.credentials)
            user_id = int(payload.get("sub", 0))
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if user and user.is_active and user.role == UserRole.SUPER_ADMIN:
                return True
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Requires SUPER_ADMIN role or valid secret token header.",
    )


router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])


@router.post(
    "/webhook",
    summary="Receive and process incoming Telegram webhook updates",
)
async def telegram_webhook(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db),
):
    """
    Receives incoming updates from Telegram's webhook server.
    Secured with constant-time comparison on X-Telegram-Bot-Api-Secret-Token.
    Fails safely if the webhook secret is not configured.
    """
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected_secret:
        logger.error("Rejected Telegram webhook: TELEGRAM_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret is not configured on the server.",
        )

    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected_secret
    ):
        logger.warning("Rejected Telegram webhook: invalid secret token header.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram secret token header.",
        )

    handler = TelegramHandler(session=session)
    await handler.process_update(update)
    return {"ok": True}


@router.post(
    "/webhook/setup",
    response_model=ApiResponse[dict],
    summary="Configure Telegram Webhook with secret token (Admin or Secret Header)",
)
async def setup_webhook(
    webhook_url: str,
    _auth: bool = Depends(require_admin_or_secret),
):
    """
    Admin helper to register the public webhook URL with Telegram's Bot API.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_BOT_TOKEN is not configured on the server.",
        )
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_WEBHOOK_SECRET is not configured on the server.",
        )

    client = TelegramClient()
    res = await client.set_webhook(
        url=webhook_url,
        secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
        drop_pending_updates=False,
    )
    if not res.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set Telegram webhook: {res.get('description')}",
        )
    return success_response(data=res, message="Telegram webhook registered successfully.")


@router.get(
    "/webhook/info",
    response_model=ApiResponse[dict],
    summary="Check Telegram Webhook status (Admin or Secret Header)",
)
async def get_webhook_status(
    _auth: bool = Depends(require_admin_or_secret),
):
    """
    Admin helper to inspect the registered webhook status from Telegram Bot API.
    Does not reveal secret tokens or bot tokens.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_BOT_TOKEN is not configured on the server.",
        )
    client = TelegramClient()
    res = await client.get_webhook_info()
    return success_response(data=res, message="Telegram webhook info retrieved.")


@router.get(
    "/me",
    response_model=ApiResponse[dict],
    summary="Verify Telegram bot identity via getMe (Admin or Secret Header)",
)
async def get_bot_identity(
    _auth: bool = Depends(require_admin_or_secret),
):
    """
    Admin helper to verify Telegram bot identity via getMe.
    Does not reveal the bot token.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_BOT_TOKEN is not configured on the server.",
        )
    client = TelegramClient()
    res = await client.get_me()
    if not res.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telegram API getMe failed: {res.get('description', res.get('error'))}",
        )
    return success_response(data=res.get("result", {}), message="Telegram bot identity verified.")
