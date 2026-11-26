from pydantic import BaseModel
from typing import Literal

class EmailDraft(BaseModel):
    draft_id: str
    telegram_id: int
    to: str
    subject: str
    body: str
    thread_id: str = ""
    status: Literal["pending", "sent", "cancelled"] = "pending"

