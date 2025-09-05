#!/usr/bin/env python3
"""
Minimal Telegram bot in webhook mode using FastAPI + python-telegram-bot v20.
"""

import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request

import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")  

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

# Create PTB application
application = Application.builder().token(BOT_TOKEN).build()

# Handlers
async def start(update, _context):
    await update.message.reply_text("👋 Hello! Webhook bot is working!")

async def echo(update, _context):
    await update.message.reply_text(f"Echo: {update.message.text}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# Lifespan handler for FastAPI (PEP 646)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Initializing PTB Application...")
    await application.initialize()
    await application.start()
    if WEBHOOK_URL:
        logger.info(f"🔗 Setting webhook to {WEBHOOK_URL}")
        await application.bot.set_webhook(WEBHOOK_URL)
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
