from pydantic import BaseModel


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
