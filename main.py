"""FastAPI application composition and lifecycle only."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from db.mongo import close_db, connect_to_db
from gmail.pubsub import renew_expiring_watches
from routes.gmail import router as gmail_router
from routes.system import router as system_router

load_dotenv()
logger = logging.getLogger(__name__)


async def watch_renewal_loop():
    """Daily maintenance only; Gmail message changes are handled by Pub/Sub."""
    while True:
        try:
            await renew_expiring_watches()
        except Exception:
            logger.exception("Gmail watch renewal pass failed")
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    telegram_app = None
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from telegram_bot.app import create_telegram_application
        telegram_app = create_telegram_application()
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()
    renewal_task = asyncio.create_task(watch_renewal_loop())
    yield
    renewal_task.cancel()
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    await close_db()


app = FastAPI(title=os.getenv("PROJECT_NAME", "Email Manager Agent"), lifespan=lifespan)
app.include_router(system_router)
app.include_router(gmail_router)
