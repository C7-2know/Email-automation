"""MongoDB connection and small account repository helpers."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from models.gmail_account import GmailAccount
from utils.time import utcnow

_client = None
_db = None



async def connect_to_db():
    global _client, _db
    _client = AsyncIOMotorClient(os.environ["MONGO_URI"])
    _db = _client[os.getenv("MONGO_DB_NAME", "gmail_bot")]
    await _client.admin.command("ping")
    await migrate_legacy_account_arrays()
    await ensure_indexes()


async def close_db():
    if _client:
        _client.close()


def get_collection(name: str):
    if _db is None:
        raise RuntimeError("Database connection not established")
    return _db[name]


async def ensure_indexes():
    await get_collection("gmail_accounts").create_index(
        "email", unique=True, partialFilterExpression={"email": {"$type": "string"}}
    )
    await get_collection("processed_emails").create_index(
        [("account_id", ASCENDING), ("gmail_message_id", ASCENDING)], unique=True
    )
    await get_collection("email_drafts").create_index("draft_id", unique=True)
    await get_collection("email_drafts").create_index("telegram_id")
    await get_collection("users").create_index("telegram_id", unique=True)


async def migrate_legacy_account_arrays():
    """Copy the original `{telegram_id, accounts: [...]}` layout without deleting it."""
    async for user in get_collection("gmail_accounts").find({"accounts": {"$exists": True}}):
        for account in user.get("accounts", []):
            email = account.get("email")
            if not email:
                continue
            await get_collection("gmail_accounts").update_one(
                {"email": email.lower()},
                {"$setOnInsert": {
                    "telegram_id": user["telegram_id"], "email": email.lower(), "provider": "gmail",
                    "access_token": account.get("access_token"), "refresh_token": account.get("refresh_token"),
                    "token_expiry": account.get("token_expiry", account.get("expiry")), "enabled": True,
                    "created_at": utcnow(), "updated_at": utcnow(),
                }}, upsert=True,
            )