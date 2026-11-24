import os
from telegram.ext import Application
from telegram_bot.handler import register_handlers

def create_telegram_application():
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    register_handlers(app)
    return app
