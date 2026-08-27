import logging
from fastapi import APIRouter, HTTPException, Request
from db.mongo import find_gmail_account
from gmail.sync import sync_account
from services.notifications import notify_telegram
from utils.pubsub import decode_gmail_pubsub_payload, verify_pubsub_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["gmail"])

@router.post("/gmail/webhook", status_code=200)
async def gmail_webhook(request: Request):
    """Handle Gmail Pub/Sub webhook notifications for new emails."""
    await verify_pubsub_request(request)
    try:
        email, history_id = decode_gmail_pubsub_payload(await request.json())
    except ValueError:
        # Acknowledge malformed input so Pub/Sub does not redeliver it indefinitely.
        logger.warning("Ignored malformed Gmail Pub/Sub push")
        return {"status": "ignored"}
    account = await find_gmail_account(email)
    if not account or not account.get("enabled", True):
        return {"status": "ignored"}
    try:
        await sync_account(account, history_id, notify_telegram)
    except Exception:
        logger.exception("Gmail sync failed for account=%s history=%s", email, history_id)
        raise HTTPException(503, "temporary Gmail synchronization failure")
    return {"status": "ok"}

@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback from Gmail and connect the account to the user's Telegram ID."""
    from gmail.auth import handle_oauth_callback
    try:
        email = await handle_oauth_callback(code, int(state))
    except (ValueError, KeyError):
        raise HTTPException(400, "Invalid OAuth state")
    return {"status": "connected", "email": email}
