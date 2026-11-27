from pydantic import BaseModel

class TelegramUser(BaseModel):
    telegram_id: int
    name: str | None = None
    mode: str = "idle"
    current_draft_id: str | None = None
