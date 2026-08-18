# Gmail Telegram notifier

Gmail sends a mailbox-change event to Google Cloud Pub/Sub; Pub/Sub pushes it to `POST /gmail/webhook`. The event contains only `emailAddress` and `historyId`, never the message. The application uses Gmail History API to find added messages, de-duplicates them in MongoDB, analyzes them once, and sends conservative Telegram notifications.

## Setup

Create a Gmail API OAuth web client, enable Gmail API and Pub/Sub, and grant the Gmail service account publisher permission on the configured Pub/Sub topic. Create an authenticated push subscription for `https://YOUR_HOST/gmail/webhook`, using `GMAIL_PUBSUB_AUDIENCE` as its OIDC audience. Configure its values from `.env.example`; the OAuth redirect URI must be `PUBLIC_BASE_URL/oauth/callback` and the required Gmail scopes are readonly, send, and modify.

Run locally with `uvicorn main:app --reload`; expose the webhook with a HTTPS tunnel during development. Run unit checks with `pytest`. Watches are renewed daily by the app's maintenance loop (or this can be replaced by Cloud Scheduler); this loop does not fetch email.

Install dependencies before starting: `python -m pip install -r requirements.txt`. The integration package is named `telegram_bot/`, not `telegram/`, because a local `telegram` folder would shadow the external `python-telegram-bot` package.

When a saved History cursor has expired, the service establishes the Pub/Sub history ID as a fresh baseline rather than backfilling, avoiding duplicate notifications.
