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
from telegram_bot.app import create_telegram_application
from db.redis import connect_redis, close_redis

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
    telegram_app = None
    renewal_task = None

    await connect_to_db()
    await connect_redis()

    try:
        logger.info("MongoDB connected successfully")
        logger.info("Redis connected successfully")

        if os.getenv("TELEGRAM_BOT_TOKEN"):
            telegram_app = create_telegram_application()
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling()
            logger.info("Telegram connected successfully!")
        renewal_task = asyncio.create_task(watch_renewal_loop())
        
        yield
        
    finally: 
        logger.info("Application shutdown started")
        if renewal_task:
            renewal_task.cancel()
            try:
                await renewal_task
            except asyncio.CancelledError:
                pass

        if telegram_app:
            if telegram_app.updater.running:
                await telegram_app.updater.stop()

            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram bot stopped")

        await close_redis()
        await close_db()

        logger.info("Application shutdown completed")


app = FastAPI(title=os.getenv("PROJECT_NAME", "Email Manager Agent"), lifespan=lifespan)
app.include_router(system_router)
app.include_router(gmail_router)
