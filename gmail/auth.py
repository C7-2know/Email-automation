import asyncio
import logging
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from repositories.gmail_account import GmailAccounts as gmail_accounts
from utils.state import create_oauth_state
from db.redis import get_redis


SCOPES =[
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

logger = logging.getLogger(__name__)

def _flow(state:str | None, code_verifier: str | None = None,):
    base_url = os.environ.get("PUBLIC_BASE_URL","").rstrip("/")
    client_config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{base_url}/oauth/callback"]
        }
    }
    return Flow.from_client_config(
        client_config, scopes=SCOPES,
        redirect_uri=f"{base_url}/oauth/callback", 
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=(code_verifier is None),
        )

async def get_auth_url(telegram_id: int) -> str:
    redis = get_redis()
    
    state = await create_oauth_state(redis, telegram_id)

    flow = _flow(state)

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    verifier = flow.code_verifier

    if not verifier:
        raise RuntimeError("Failed to generate PKCE code verifier")

    # Save the verifier using the same state
    await redis.set(
        f"oauth:verifier:{state}",
        verifier,
        ex=600,
    )

    return auth_url

async def handle_oauth_callback(code: str, telegram_id: int, state: str):

    redis = get_redis()
    verifier = await redis.getdel(f"oauth:verifier:{state}")

    if not verifier:
        raise ValueError("PKCE verifier missing or expired")

    flow = _flow(state, code_verifier=verifier)
    await asyncio.to_thread(flow.fetch_token, code=code)
    credentials = flow.credentials

    # get email address
    service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    profile = await asyncio.to_thread(service.users().getProfile(userId='me').execute)
    email = profile['emailAddress']

    gmail_account_repo = gmail_accounts()

    account = await gmail_account_repo.create_or_update_gmail_account(telegram_id, email, credentials)
    try:
        from gmail.pubsub import create_or_renew_watch
        await create_or_renew_watch(account)
    except Exception:
        logger.exception("Could not create Gmail watch for account=%s", email)
    return email

async def build_gmail_service(account: dict):
    """Builds a Gmail API service using stored credentials."""
    credentials = create_credentials(account)

    if credentials.expired and credentials.refresh_token:
        await asyncio.to_thread(credentials.refresh, Request())

        await gmail_accounts.update_tokens(
            account_id=account["_id"],
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=credentials.expiry
        )

    if not credentials.valid:
        raise ValueError(
            f"Account {account.get('email')} needs to be reconnected."
        )
    service = await asyncio.to_thread(build, 'gmail', 'v1', credentials=credentials, cache_discovery=False)
    return service


def create_credentials(account: dict) -> Credentials:
    return Credentials(
        token=account.get("access_token"),
        refresh_token=account.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )