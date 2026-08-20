import asyncio
import base64
import json
import os
from fastapi import HTTPException, Request


def decode_gmail_pubsub_payload(payload: dict) -> tuple[str, str]:
    """Extract the mailbox address and History API cursor from a Pub/Sub push."""
    try:
        encoded = payload["message"]["data"]
        value = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4)))
        email, history_id = value["emailAddress"], value["historyId"]
        if not isinstance(email, str) or not history_id:
            raise ValueError("missing Gmail notification fields")
        return email.lower(), str(history_id)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Pub/Sub Gmail payload") from exc


async def verify_pubsub_request(request: Request) -> None:
    """Validate an authenticated Pub/Sub push when an audience is configured."""
    audience = os.getenv("GMAIL_PUBSUB_AUDIENCE")
    if not audience:
        return
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing Pub/Sub identity token")
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token
    try:
        await asyncio.to_thread(id_token.verify_oauth2_token, authorization[7:], GoogleRequest(), audience)
    except Exception as exc:
        raise HTTPException(401, "invalid Pub/Sub identity token") from exc
