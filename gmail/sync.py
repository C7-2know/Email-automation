"""Mailbox change synchronization driven by Gmail Pub/Sub, not email polling."""
import asyncio
import logging
from pymongo.errors import DuplicateKeyError
from googleapiclient.errors import HttpError
from db.mongo import get_collection, utcnow
from gmail.auth import build_gmail_service
from gmail.parser import parse_gmail_message
from ai.email_analyzer import analyze_email
from models.processed_email import ProcessedEmail

logger = logging.getLogger(__name__)

async def _execute(request):
    return await asyncio.to_thread(request.execute)

async def _history_messages(service, start_history_id):
    """Fetch all messages added since the given history ID."""
    page_token, message_ids, newest = None, set(), str(start_history_id)
    while True:
        response = await _execute(service.users().history().list(
            userId="me", startHistoryId=str(start_history_id), historyTypes=["messageAdded"], pageToken=page_token))
        newest = str(response.get("historyId", newest))
        for item in response.get("history", []):
            for added in item.get("messagesAdded", []):
                message_ids.add(added["message"]["id"])
        page_token = response.get("nextPageToken")
        if not page_token: return message_ids, newest

async def _process_message(account, service, message_id, notify):
    processed = get_collection("processed_emails")
    claim = ProcessedEmail(account_id=account["_id"], 
                           telegram_id=account["telegram_id"],
                           gmail_message_id=message_id, 
                           processed_at=utcnow()).model_dump(exclude_none=True)
    try:
        await processed.insert_one(claim)
    except DuplicateKeyError:
        return False
    try:
        raw = await _execute(service.users().messages().get(userId="me", id=message_id, format="full"))
        email = parse_gmail_message(raw)
        analysis = await analyze_email(email)
        record = {**email.model_dump(), **analysis.model_dump(), "status": "processed"}
        await processed.update_one({"_id": claim["_id"]}, {"$set": record})
        if analysis.should_notify:
            notification = await processed.find_one({"account_id": account["_id"], "gmail_message_id": message_id})
            await notify(account, notification)
            await processed.update_one({"_id": notification["_id"]}, {"$set": {"notified_at": utcnow()}})
            print(f"Notification sent for message {message_id} to Telegram ID {account['telegram_id']}")
        return True
    except Exception:
        # Do not retain a partial claim: a later Pub/Sub delivery can safely retry it.
        await processed.delete_one({"_id": claim["_id"]})
        raise

async def sync_account(account, notification_history_id, notify):
    """Process changes since the saved cursor and advance it only on full success."""
    previous = account.get("history_id")
    if not previous:
        await get_collection("gmail_accounts").update_one({"_id": account["_id"]}, {"$set": {"history_id": str(notification_history_id)}})
        return 0
    service =await build_gmail_service(account)
    try:
        message_ids, newest = await _history_messages(service, previous)
    except HttpError as exc:
        if exc.resp.status == 404:  # Gmail history cursor expired: establish baseline, no backfill/duplicates.
            logger.warning("Expired history cursor for account=%s", account.get("email"))
            await get_collection("gmail_accounts").update_one({"_id": account["_id"]}, {"$set": {"history_id": str(notification_history_id), "updated_at": utcnow()}})
            return 0
        raise
    for message_id in message_ids:
        await _process_message(account, service, message_id, notify)
    await get_collection("gmail_accounts").update_one({"_id": account["_id"]}, {"$set": {"history_id": newest, "updated_at": utcnow()}})
    return len(message_ids)
