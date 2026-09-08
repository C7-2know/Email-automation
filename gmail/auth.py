import asyncio
import logging
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from db.mongo import save_gmail_account


SCOPES =[
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

logger = logging.getLogger(__name__)

def _flow():
    return Flow.from_client_secrets_file(
        os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", "google_credentials.json"), scopes=SCOPES,
        redirect_uri=f"{os.environ['PUBLIC_BASE_URL'].rstrip('/')}/oauth/callback")

def get_auth_url(telegram_id: int) -> str:
    flow = _flow()

    auth_url, _ = flow.authorization_url(
        state=str(telegram_id),
        access_type="offline",
        prompt="consent"
    )

    return auth_url

async def handle_oauth_callback(code: str, telegram_id: int):
    flow = _flow()
    await asyncio.to_thread(flow.fetch_token, code=code)
    credentials = flow.credentials

    # get email address
    service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    profile = await asyncio.to_thread(service.users().getProfile(userId='me').execute)
    email = profile['emailAddress']

    account = await save_gmail_account(telegram_id, email, credentials)
    try:
        from gmail.pubsub import create_or_renew_watch
        await create_or_renew_watch(account)
    except Exception:
        logger.exception("Could not create Gmail watch for account=%s", email)
    return email

def build_gmail_service(account: dict):
    """Builds a Gmail API service using stored credentials."""
    creds = Credentials(
        token=account["access_token"],
        refresh_token=account["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)
