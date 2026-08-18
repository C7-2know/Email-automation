"""Email-domain models shared by Gmail synchronization and AI analysis."""
from typing import Literal
from pydantic import BaseModel, Field


class GmailMessage(BaseModel):
    gmail_message_id: str
    thread_id: str
    sender: str = ""
    sender_email: str = ""
    recipient: str = ""
    subject: str = "(no subject)"
    date: str = ""
    snippet: str = ""
    body: str = ""


class EmailAnalysis(BaseModel):
    is_spam: bool
    category: Literal["Work", "Personal", "Newsletter", "Finance", "Urgent", "Notification", "Spam"]
    priority: Literal["High", "Medium", "Low"]
    importance_score: float = Field(ge=0, le=1)
    should_notify: bool
    summary: str
    action: str = "none"
    deadline: str = "none"
