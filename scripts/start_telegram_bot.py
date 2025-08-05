#!/usr/bin/env python3
"""
Local Telegram Bot Testing Script
Runs the intelligent conversation system through Telegram polling
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY", 
        "DATABASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please ensure your .env file contains all required variables.")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

async def start_telegram_bot():
    """Start the Telegram bot in polling mode"""
    logger.info("🚀 Starting Smart Personal Planner Telegram Bot...")
    logger.info("🧠 Intelligent Conversation System: ACTIVE")
    logger.info("🎯 Plan Management Workflow: READY")
    logger.info("💬 Multi-Agent LangGraph: INITIALIZED")
    
    try:
        from app.routers.telegram import run_telegram_polling
        await run_telegram_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        raise

def main():
    """Main function to start the bot"""
    print("🤖 Smart Personal Planner - Telegram Bot Testing")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    print("\n📋 Testing Instructions:")
    print("1. Open your Telegram app")
    print("2. Find your bot (search for your bot username)")
    print("3. Start a conversation with /start")
    print("4. Test intelligent conversations:")
    print("   • 'Hello' (greeting)")
    print("   • 'What is a project goal?' (question)")
    print("   • 'I want to learn Python in 6 months' (plan management)")
    print("   • 'Can you refine my last plan?' (refinement)")
    print("5. Press Ctrl+C to stop the bot")
    
    input("\nPress Enter when ready to start the bot...")
    
    try:
        asyncio.run(start_telegram_bot())
    except KeyboardInterrupt:
        print("\n✅ Bot testing completed!")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
