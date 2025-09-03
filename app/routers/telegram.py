# app/routers/telegram.py
import logging
import os
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.orchestration.message_handler import handle_user_message

from app.db.db import get_db
from app.db.memory_repository import MemoryRepository

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
application = Application.builder().token(BOT_TOKEN).build()


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram updates via webhook and process them with Application."""
    data = await request.json()
    update = telegram.Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# --- Command handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("👋 Hello! I’m your Smart Planner Bro! How can I help you today?")


# --- Message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        logger.error("No effective_user in update")
        return
    user_id = update.effective_user.id
    if update.message is None or update.message.text is None:
        logger.error("No message or message text in update")
        return
    user_message = update.message.text

    with next(get_db()) as db:
        repo = MemoryRepository(db)
        memory_context = repo.get_memory_context(user_id)

    logger.info(f"[Telegram] user_id={user_id}, message={user_message!r}")

    try:
        response_text = await handle_user_message(user_id, user_message, memory_context)
    except Exception as e:
        logger.exception(f"Error handling user message: {e}")
        response_text = "❌ Sorry, something went wrong while processing your request."

    # save updates back (if any): https://docs.google.com/document/d/1YE0nNw6qEGp56JzPdLklilnbDAMSdAspQTQnwIKrmv8/edit?tab=t.dkxl7jj1w70f#heading=h.rxhon89h3ebx
        if hasattr(memory_context, "memory_updates") and memory_context.memory_updates:
            repo.save_memory_updates(user_id, memory_context.memory_updates)

    await update.message.reply_text(response_text, parse_mode="Markdown")


# --- Setup and run ---
def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Telegram bot is running...")
    app.run_polling()
