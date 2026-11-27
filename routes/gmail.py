import logging
from fastapi import APIRouter, HTTPException, Request, Query
from repositories.gmail_account import GmailAccounts 
from gmail.sync import sync_account
from services.notifications import notify_telegram
from utils.pubsub import decode_gmail_pubsub_payload, verify_pubsub_request
from utils.state import consume_oauth_state
from db.redis import get_redis

from gmail.auth import handle_oauth_callback

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
    gmail_accounts = GmailAccounts()
    account = await gmail_accounts.get_gmail_account_by_email(email)
    if not account or not account.get("enabled", True):
        return {"status": "ignored"}
    try:
        await sync_account(account, history_id, notify_telegram)
    except Exception:
        logger.exception("Gmail sync failed for account=%s history=%s", email, history_id)
        raise HTTPException(503, "temporary Gmail synchronization failure")
    return {"status": "ok"}

@router.get("/oauth/callback")
async def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    ):
    """Handle OAuth callback from Gmail and connect the account to the user's Telegram ID."""
    if error:
        raise HTTPException(400, "Google authorization was not completed")


    if not state or not code:
        raise HTTPException(400, "Missing OAuth state or code")

    redis = get_redis()
    state_data = await consume_oauth_state(redis, state)

    if state_data is None:
        raise HTTPException(400, "Invalid or expired OAuth state")
    
    if state_data["provider"] != "gmail":
        raise HTTPException(400, "Invalid OAuth provider")

    telegram_id = int(state_data["telegram_id"])

    email = await handle_oauth_callback(code, telegram_id, state)

    return {
        "message": "Gmail account connected successfully",
        "email": email,
    }