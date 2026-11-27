from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel
    

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
