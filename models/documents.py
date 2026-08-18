"""MongoDB document contracts used when application records are created."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class GmailAccount(BaseModel):
    telegram_id: int
    email: str
    provider: Literal["gmail"] = "gmail"
    access_token: str | None = None
    refresh_token: str | None = None
    token_expiry: str | None = None
    enabled: bool = True
    history_id: str | None = None
    watch_expiration: datetime | None = None
    watch_topic: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProcessedEmail(BaseModel):
    account_id: Any
    telegram_id: int
    gmail_message_id: str
    thread_id: str = ""
    sender: str = ""
    sender_email: str = ""
    recipient: str = ""
    subject: str = "(no subject)"
    date: str = ""
    snippet: str = ""
    body: str = ""
    category: str | None = None
    priority: str | None = None
    importance_score: float | None = None
    should_notify: bool | None = None
    summary: str | None = None
    action: str | None = None
    deadline: str | None = None
    status: Literal["processing", "processed"] = "processing"
    processed_at: datetime
    notified_at: datetime | None = None


class EmailDraft(BaseModel):
    draft_id: str
    telegram_id: int
    to: str
    subject: str
    body: str
    thread_id: str = ""
    status: Literal["pending", "sent", "cancelled"] = "pending"


class TelegramUser(BaseModel):
    telegram_id: int
    name: str | None = None
    mode: str = "idle"
    current_draft_id: str | None = None
