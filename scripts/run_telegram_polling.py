#!/usr/bin/env python3
"""
Local Telegram Bot Testing Script
Runs the Smart Personal Planner Telegram bot in polling mode.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Load env vars
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Environment check ---
def check_environment() -> bool:
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "DATABASE_URL"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"❌ Missing env vars: {', '.join(missing)}")
        logger.error("Please ensure your .env file contains all required variables.")
        return False
    logger.info("✅ All required environment variables are set")
    return True

# --- Handlers ---
async def start(update, context):
    await update.message.reply_text("👋 Hello! I’m your Smart Planner Bot.")

async def handle_message(update, context):
    from app.orchestration.message_handler import handle_user_message
    from app.db.db import get_db
    from app.db.memory_repository import MemoryRepository
    from app.cognitive.contracts.types import MemoryContext

    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"[Telegram] user_id={user_id}, message={user_message!r}")


    try:
        db = next(get_db())
        try:
            repo = MemoryRepository(db)
            memory_context = repo.get_memory_context(user_id)
            response_text = await handle_user_message(user_id, user_message, memory_context)
            repo.save_memory_updates(user_id, memory_context.memory_updates)
        finally:
            db.close()
    except Exception:
        logger.exception("Error in handle_message")
        response_text = "❌ Sorry, something went wrong."

    await update.message.reply_text(response_text, parse_mode="Markdown")

# --- Main bot runner ---
async def run_telegram_polling():
    logger.info("🚀 Starting Smart Planner Bot (polling mode)...")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
    await app.run_polling()

def main():
    print("🤖 Smart Personal Planner - Telegram Bot Testing")
    print("=" * 50)

    if not check_environment():
        return 1

    print("\n📋 Testing Instructions:")
    print("1. Open Telegram and find your bot (search by username)")
    print("2. Start with /start")
    print("3. Try messages like:")
    print("   • 'Hello'")
    print("   • 'What is a project goal?'")
    print("   • 'I want to learn Python in 6 months'")
    print("   • 'Can you refine my last plan?'")
    print("4. Press Ctrl+C to stop the bot\n")

    input("Press Enter when ready to start the bot...")

    try:
        import asyncio
        asyncio.run(run_telegram_polling())
    except KeyboardInterrupt:
        print("\n✅ Bot stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
