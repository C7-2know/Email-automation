"""Telegram commands and notification callbacks."""
from db.mongo import get_collection
from gmail.auth import get_auth_url
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from models.telegram_user import TelegramUser
from repositories.users import UserRepository

user_repository = UserRepository()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await user_repository.upsert_user(telegram_id=user.id, name=user.full_name or user.first_name)
    await update.message.reply_text("Welcome!\n/connect — add Gmail\n/accounts — view connected accounts\n/disconnect — remove an account")

async def connect_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth_url =  await get_auth_url(update.effective_user.id)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Connect Google Account",
                url=auth_url
            )
        ]
    ])
    await update.message.reply_text( "Click below to connect your Gmail account:", reply_markup=keyboard)

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = [a async for a in get_collection("gmail_accounts").find({"telegram_id": update.effective_user.id})]
    if not accounts:
        await update.message.reply_text("No accounts connected. Use /connect to add one.")
        return
    lines = [f"{index}. {a['email']} {'✅' if a.get('enabled', True) else '⏸️'}" for index, a in enumerate(accounts, 1)]
    buttons = [[InlineKeyboardButton(f"Disconnect {a['email']}", callback_data=f"disc:{str(a['_id'])}")] for a in accounts]
    await update.message.reply_text("Connected Gmail accounts:\n" + "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_accounts(update, context)

async def send_email_notification(bot, account: dict, processed: dict):
    priority = processed.get("priority", "Low")
    priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
    category = processed.get("category", "Notification")
    text = (f"{priority_emoji} {category} • {priority}\n\nAccount: {account['email']}\n"
            f"From: {processed.get('sender', '')}\nSubject: {processed.get('subject', '')}\n\n{processed.get('summary', '')}")
    if processed.get("action") not in (None, "", "none"): text += f"\n\nAction: {processed['action']}"
    if processed.get("deadline") not in (None, "", "none"): text += f"\nDeadline: {processed['deadline']}"
    notification_id = str(processed["_id"])
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Reply", callback_data=f"n:r:{notification_id}"), InlineKeyboardButton("Mark important", callback_data=f"n:i:{notification_id}")], [InlineKeyboardButton("Skip", callback_data=f"n:s:{notification_id}")]])
    await bot.send_message(chat_id=account["telegram_id"], text=text, reply_markup=keyboard)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query, user_id = update.callback_query, update.effective_user.id
    await query.answer()
    parts = query.data.split(":")
    if parts[0] == "disc" and len(parts) == 2:
        from bson import ObjectId
        result = await get_collection("gmail_accounts").delete_one({"_id": ObjectId(parts[1]), "telegram_id": user_id})
        await query.edit_message_text("Account disconnected." if result.deleted_count else "Account not found.")
        return
    if len(parts) != 3 or parts[0] != "n": return
    from bson import ObjectId
    notification = await get_collection("processed_emails").find_one({"_id": ObjectId(parts[2]), "telegram_id": user_id})
    if not notification:
        await query.message.reply_text("This notification is no longer available.")
        return
    if parts[1] == "i":
        await get_collection("processed_emails").update_one({"_id": notification["_id"]}, {"$set": {"marked_important": True}})
        await query.edit_message_reply_markup(reply_markup=None); await query.message.reply_text("Marked as important.")
    elif parts[1] == "s":
        await query.edit_message_reply_markup(reply_markup=None); await query.message.reply_text("Skipped.")
    elif parts[1] == "r":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Drafting reply…")
        account = await get_collection("gmail_accounts").find_one({"_id": notification["account_id"], "telegram_id": user_id})
        if not account:
            await query.message.reply_text("The connected account is no longer available.")
            return
        from gmail.auth import build_gmail_service
        from ai.agent_graph import build_reply_agent
        from langchain_core.messages import HumanMessage
        agent = await build_reply_agent(build_gmail_service(account), user_id)
        result = await agent.ainvoke({"messages": [HumanMessage(content=f"Draft a reply to thread {notification['thread_id']}. Use get_email_thread then save_draft.")]})
        draft_id = next((str(m.content).split("DRAFT_SAVED:")[-1].strip() for m in result["messages"] if "DRAFT_SAVED:" in str(getattr(m, "content", ""))), "")
        draft = await get_collection("email_drafts").find_one({"draft_id": draft_id, "telegram_id": user_id})
        if not draft:
            await query.message.reply_text("Could not prepare a draft reply.")
            return
        await query.message.reply_text(f"Draft reply ready:\n\nTo: {draft['to']}\nSubject: {draft['subject']}\n\n{draft['body']}")

def register_handlers(application):
    from telegram.ext import CallbackQueryHandler, CommandHandler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect_gmail))
    application.add_handler(CommandHandler("accounts", list_accounts))
    application.add_handler(CommandHandler("disconnect", disconnect))
    application.add_handler(CallbackQueryHandler(handle_button))
