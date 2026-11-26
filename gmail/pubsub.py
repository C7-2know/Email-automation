import asyncio
import logging
import os
from datetime import datetime, timezone
from gmail.auth import build_gmail_service
from db.mongo import get_collection, utcnow

logger = logging.getLogger(__name__)

def topic_name():
    topic = os.environ["GMAIL_PUBSUB_TOPIC"]
    if topic.startswith("projects/"):
        return topic
    
    return f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/topics/{topic}"

async def create_or_renew_watch(account):
    service = await build_gmail_service(account)
    response = await asyncio.to_thread(
        service.users().watch(userId="me", body={"topicName": topic_name(), "labelIds": ["INBOX"]}).execute
        )
    update = {
        "watch_expiration": datetime.fromtimestamp(int(response["expiration"])/1000, timezone.utc), 
        "watch_topic": topic_name(), 
        "updated_at": utcnow()
        }
    if not account.get("history_id"):
        update["history_id"] = response["historyId"]

    await get_collection("gmail_accounts").update_one(
        {"_id": account["_id"]}, {"$set": update}
        )
    return response

async def renew_expiring_watches(within_hours=24):
    cutoff = datetime.now(timezone.utc).timestamp() + within_hours * 3600
    collection = get_collection("gmail_accounts")
    cursor = collection.find({"enabled": True})

    async for account in cursor:
        expiry = account.get("watch_expiration")

        if not expiry or expiry.timestamp() <= cutoff:
            try:
                await create_or_renew_watch(account)
            except Exception:
                logger.exception(
                    "Failed to renew Gmail watch for %s",
                    account.get("email"),
                )
