import os


async def notify_telegram(account: dict, processed: dict) -> None:
    """Deliver an already-classified important email to its owning Telegram user."""
    # Lazy imports prevent a missing optional Telegram dependency from stopping
    # FastAPI routes from loading; sending a Telegram notification still needs it.
    from telegram import Bot
    from telegram_bot.handler import send_email_notification
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    async with Bot(token) as bot:
        await send_email_notification(bot, account, processed)
