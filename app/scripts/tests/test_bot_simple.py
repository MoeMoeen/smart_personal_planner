#!/usr/bin/env python3
"""
Simple Telegram Bot Test - Step by step debugging
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_bot():
    """Test bot functionality step by step"""
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found")
        return
    
    print("✅ Token found")
    print("🚀 Testing Telegram bot initialization...")
    
    try:
        from telegram.ext import Application
        
        # Create application
        print("📱 Creating application...")
        application = Application.builder().token(token).build()
        
        print("🔧 Initializing application...")
        await application.initialize()
        
        print("🔧 Starting application...")
        await application.start()
        
        # Get bot info
        bot_info = await application.bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"🤖 Bot username: @{bot_info.username}")
        print(f"🆔 Bot ID: {bot_info.id}")
        print(f"📝 Bot name: {bot_info.first_name}")
        
        print("🔧 Stopping application...")
        await application.stop()
        await application.shutdown()
        
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot())
