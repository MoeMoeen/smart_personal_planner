#!/usr/bin/env python3
"""
Local Telegram Bot Testing Script

This script runs the Telegram bot in polling mode for local development and testing.
No webhook setup required - the bot will directly poll Telegram for messages.

Usage:
1. Set TELEGRAM_BOT_TOKEN in your .env file
2. Run: python test_telegram_local.py
3. Send messages to your bot on Telegram
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our Telegram bot functionality
from app.routers.telegram import run_telegram_polling

def main():
    """Main function to run the Telegram bot locally"""
    
    # Check if token is set
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        print("📝 Please add it to your .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather")
        return
    
    print("🚀 Starting Telegram bot in local polling mode...")
    print("📱 Go to Telegram and send messages to your bot!")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Run the bot
        asyncio.run(run_telegram_polling())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped. Goodbye!")

if __name__ == "__main__":
    main()
