"""Safe extraction of readable content from Gmail API messages."""
import base64
import html
import re
from email.utils import parseaddr
from models.gmail_message import GmailMessage

def _decode(data):
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
    except Exception:
        return ""

def _html_to_text(value):
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", value))).strip()

def _parts(part):
    body = _decode(part.get("body", {}).get("data", ""))
    if part.get("mimeType") == "text/plain" and body:
        yield "plain", body
    elif part.get("mimeType") == "text/html" and body:
        yield "html", _html_to_text(body)
    for child in part.get("parts", []) or []:
        yield from _parts(child)

def parse_gmail_message(message, max_body_chars=8000):
    headers = {h.get("name", "").lower(): h.get("value", "") for h in message.get("payload", {}).get("headers", [])}
    candidates = list(_parts(message.get("payload", {})))
    body = next((x for kind, x in candidates if kind == "plain"), "") or next((x for kind, x in candidates if kind == "html"), "")
    sender = headers.get("from", "")
    return GmailMessage(gmail_message_id=message.get("id", ""), thread_id=message.get("threadId", ""), sender=sender,
        sender_email=parseaddr(sender)[1], recipient=headers.get("to", ""), subject=headers.get("subject", "(no subject)"),
        date=headers.get("date", ""), snippet=message.get("snippet", ""), body=body[:max_body_chars])
