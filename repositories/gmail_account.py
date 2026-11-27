from db.mongo import get_collection
from utils.time import utcnow
from models.gmail_account import GmailAccount
from datetime import datetime, timezone
from bson import ObjectId

class GmailAccounts:       

    async def get_gmail_account_by_email(self, email: str) -> dict:
        """Retrieve a Gmail account document by email address."""
        collection = get_collection("gmail_accounts")
        account = await collection.find_one({"email": email.lower()})
        if not account:
            raise ValueError(f"No Gmail account found for email: {email}")
        return account


    async def create_or_update_gmail_account(self, telegram_id: int, email: str, credentials):
        """Upsert one independent account per mailbox (not an array per user)."""
        now = utcnow()
        collection = get_collection("gmail_accounts")
        account = GmailAccount(
            telegram_id=telegram_id, email=email.lower(), access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=credentials.expiry.isoformat() if credentials.expiry else None,
            updated_at=now,
        ).model_dump(exclude_none=True)
        saved_account = await collection.update_one(
            {"email": email.lower()}, {"$set": account, "$setOnInsert": {"created_at": now}}, upsert=True
        )
        return saved_account

    async def update_tokens(account_id, access_token, refresh_token, token_expiry: datetime | None):
        update_data = {
            "access_token": access_token,
            "token_expiry": token_expiry,
            "updated_at": datetime.now(timezone.utc)
        }
        if refresh_token:
            update_data["refresh_token"] = refresh_token

        collection = get_collection("gmail_accounts")
        await collection.update_one(
            {"_id":ObjectId(account_id)},
            {"$set":update_data},
        )