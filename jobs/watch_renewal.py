from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gmail.pubsub import renew_expiring_watches

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        renew_expiring_watches,
        trigger="interval",
        hours=24,
        id="gmail_watch_renewal",
        replace_existing=True
    )

    scheduler.start()