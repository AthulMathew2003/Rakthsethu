import logging
import re
from typing import Any, Dict, List, Optional, Union
import httpx
from app.core.config import settings

logger = logging.getLogger("rakthasethu.telegram")


def redact_sensitive_data(text: str) -> str:
    """Redact Telegram bot token and phone numbers in logs, URLs, and exceptions."""
    val = re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot[REDACTED]", str(text))
    val = re.sub(r"(?:\+91|91|0)?[6-9]\d{9}", "[REDACTED_PHONE]", val)
    return val


def redact_telegram_token(text: str) -> str:
    return redact_sensitive_data(text)


class TelegramClient:
    """
    Lightweight, asynchronous Telegram Bot API client.
    Ensures zero token exposure in logs or error traces.
    """

    def __init__(self, token: Optional[str] = None, timeout: float = 15.0):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def _clean_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint}"

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = self._clean_url(endpoint)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if not data.get("ok"):
                    err_desc = data.get("description", "Unknown Telegram API error")
                    logger.error("Telegram API call failed: %s", redact_telegram_token(err_desc))
                return data
        except Exception as exc:
            logger.error("Telegram network call error: %s", redact_telegram_token(str(exc)))
            return {"ok": False, "error": redact_telegram_token(str(exc))}

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def edit_message_text(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("editMessageText", payload)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = show_alert
        return await self._post("answerCallbackQuery", payload)

    async def set_webhook(
        self,
        url: str,
        secret_token: Optional[str] = None,
        drop_pending_updates: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "url": url,
            "drop_pending_updates": drop_pending_updates,
        }
        if secret_token:
            payload["secret_token"] = secret_token
        return await self._post("setWebhook", payload)

    async def delete_webhook(self, drop_pending_updates: bool = False) -> Dict[str, Any]:
        return await self._post("deleteWebhook", {"drop_pending_updates": drop_pending_updates})

    async def get_webhook_info(self) -> Dict[str, Any]:
        url = self._clean_url("getWebhookInfo")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                return resp.json()
        except Exception as exc:
            logger.error("getWebhookInfo failed: %s", redact_telegram_token(str(exc)))
            return {"ok": False, "error": redact_telegram_token(str(exc))}

    async def get_me(self) -> Dict[str, Any]:
        url = self._clean_url("getMe")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                return resp.json()
        except Exception as exc:
            logger.error("getMe failed: %s", redact_telegram_token(str(exc)))
            return {"ok": False, "error": redact_telegram_token(str(exc))}

    async def get_updates(
        self,
        offset: Optional[int] = None,
        limit: int = 100,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"limit": limit, "timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        # Use longer timeout for long-polling
        try:
            async with httpx.AsyncClient(timeout=float(timeout + 10)) as client:
                resp = await client.post(self._clean_url("getUpdates"), json=payload)
                return resp.json()
        except Exception as exc:
            logger.error("getUpdates failed: %s", redact_telegram_token(str(exc)))
            return {"ok": False, "error": redact_telegram_token(str(exc))}
