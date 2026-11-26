from pydantic import BaseModel, Field
from typing import Literal

class EmailAnalysis(BaseModel):
    is_spam: bool
    category: Literal["Work", "Personal", "Newsletter", "Finance", "Urgent", "Notification", "Spam"]
    priority: Literal["High", "Medium", "Low"]
    importance_score: float = Field(ge=0, le=1)
    should_notify: bool
    summary: str
    action: str = "none"
    deadline: str = "none"
