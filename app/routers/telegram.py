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

router = APIRouter(prefix="/telegram", tags=["telegram"])

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
application = Application.builder().token(BOT_TOKEN).build()

# --- Webhook endpoint (only used if TELEGRAM_MODE=webhook) ---
@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    logger.info(f"📥 Incoming update: {data}")
    update = telegram.Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("👋 Hello! I’m your Smart Planner Bro!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.message is None or update.message.text is None:
        return
    user_id = update.effective_user.id
    user_message = update.message.text

    with next(get_db()) as db:
        repo = MemoryRepository(db)
        memory_context = repo.get_memory_context(user_id)

    try:
        response_text = await handle_user_message(user_id, user_message, memory_context)
    except Exception as e:
        logger.exception(f"Error handling user message: {e}")
        response_text = "❌ Sorry, something went wrong."

    if hasattr(memory_context, "memory_updates") and memory_context.memory_updates:
        repo.save_memory_updates(user_id, memory_context.memory_updates)

    await update.message.reply_text(response_text, parse_mode="Markdown")

# register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Optional polling runner for local dev ---
def run_polling():
    logger.info("🤖 Starting Telegram bot in POLLING mode...")
    application.run_polling()
