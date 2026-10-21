import asyncio
import logging
import signal
import sys
from typing import Optional

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.telegram.client import TelegramClient
from app.telegram.handlers import TelegramHandler
from app.telegram.schemas import TelegramUpdate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rakthasethu.telegram.polling")


async def run_polling():
    """
    Local development long-polling runner.
    Mutually exclusive with production webhooks.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured in environment or .env. Exiting.")
        sys.exit(1)

    client = TelegramClient(token=token)

    # 1. Verify Bot Token
    me_resp = await client.get_me()
    if not me_resp.get("ok"):
        logger.error("Failed to connect to Telegram Bot API. Verify your token: %s", me_resp)
        sys.exit(1)

    bot_info = me_resp.get("result", {})
    logger.info("Starting local polling for bot: @%s (ID: %s)", bot_info.get("username"), bot_info.get("id"))

    # 2. Delete active webhook so Telegram routes updates to getUpdates
    logger.info("Clearing active webhook to enable polling mode...")
    del_res = await client.delete_webhook(drop_pending_updates=False)
    if not del_res.get("ok"):
        logger.warning("Could not delete webhook: %s", del_res)

    offset: Optional[int] = None
    running = True

    def stop_signal_handler():
        nonlocal running
        logger.info("Shutdown signal received. Stopping polling loop...")
        running = False

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_signal_handler)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    logger.info("Telegram polling started. Press Ctrl+C to terminate.")

    while running:
        try:
            updates_data = await client.get_updates(offset=offset, limit=100, timeout=20)
            if not updates_data.get("ok"):
                logger.error("getUpdates returned non-ok: %s", updates_data)
                await asyncio.sleep(5)
                continue

            updates = updates_data.get("result", [])
            for raw_update in updates:
                update_obj = TelegramUpdate.model_validate(raw_update)
                offset = update_obj.update_id + 1

                async with AsyncSessionLocal() as session:
                    handler = TelegramHandler(session=session, client=client)
                    await handler.process_update(update_obj)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("Unexpected error in polling cycle: %s", exc)
            await asyncio.sleep(3)

    logger.info("Telegram polling runner finished cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
