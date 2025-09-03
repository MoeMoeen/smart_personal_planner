#!/usr/bin/env python3
"""
Minimal test bot for python-telegram-bot v20+
Confirms async handlers and polling work.
"""

import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load .env (must have TELEGRAM_BOT_TOKEN)
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("Hello! I'm your test bot.")

async def echo(update, context):
    await update.message.reply_text(update.message.text)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("🚀 Starting echo bot…")
    app.run_polling()   # ✅ sync wrapper, no asyncio issues


if __name__ == "__main__":
    main()