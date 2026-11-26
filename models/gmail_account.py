from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class GmailAccount(BaseModel):
    telegram_id: int
    email: str
    provider: Literal["gmail"] = "gmail"
    access_token: str | None = None
    refresh_token: str | None = None
    token_expiry: datetime | None = None
    enabled: bool = True
    history_id: str | None = None
    watch_expiration: datetime | None = None
    watch_topic: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


