import asyncio
import base64
import uuid
from email.mime.text import MIMEText
from langchain_core.tools import tool
from db.mongo import get_collection
from models.documents import EmailDraft

def build_reply_tools(gmail_service, telegram_id):
    """Create request-scoped tools; no Gmail service or user is held globally."""
    @tool
    async def get_email_thread(thread_id: str) -> str:
        """Read the recent messages in an email conversation."""
        try:
            thread = await asyncio.to_thread(gmail_service.users().threads().get(userId="me", id=thread_id).execute)
            rows = []
            for message in thread.get("messages", [])[-3:]:
                headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
                rows.append(f"From: {headers.get('from', '?')}\nSubject: {headers.get('subject', '?')}")
            return "\n\n---\n".join(rows)
        except Exception: return "Could not fetch this email thread."
    @tool
    async def save_draft(to: str, subject: str, body: str, thread_id: str = "") -> str:
        """Save, but do not send, an email draft."""
        draft_id = str(uuid.uuid4())
        draft = EmailDraft(draft_id=draft_id, telegram_id=telegram_id, to=to, subject=subject, body=body, thread_id=thread_id)
        await get_collection("email_drafts").insert_one(draft.model_dump())
        return f"DRAFT_SAVED:{draft_id}"
    return [get_email_thread, save_draft]

async def send_saved_draft(gmail_service, telegram_id, draft_id):
    draft = await get_collection("email_drafts").find_one({"draft_id": draft_id, "telegram_id": telegram_id, "status": "pending"})
    if not draft: return "Draft not found."
    message = MIMEText(draft["body"]); message["to"] = draft["to"]; message["subject"] = draft["subject"]
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    await asyncio.to_thread(gmail_service.users().messages().send(userId="me", body={"raw": raw, "threadId": draft.get("thread_id")}).execute)
    await get_collection("email_drafts").update_one({"_id": draft["_id"]}, {"$set": {"status": "sent"}})
    return "Email sent."
