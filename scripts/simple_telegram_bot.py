#!/usr/bin/env python3
"""
Simple Telegram Bot - Trust-Based Agent Prototype
===============================================

A simple Telegram bot using the trust-based agent approach
for comparison with the complex multi-agent system.
"""

import asyncio
import logging
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agent.simple_agent import SimplePlanningAgent

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    """
    Simple Telegram bot using the trust-based agent.
    """
    
    def __init__(self):
        self.agent = SimplePlanningAgent()
        
        # Get bot token from environment
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🧠 **Simple Planning Assistant (Prototype)**

I'm a trust-based AI assistant that relies on natural intelligence rather than rigid rules.

Just tell me what you want to achieve and I'll help you plan it!

Examples:
• "I want to read 2 books per month"
• "Help me learn guitar" 
• "Show me my latest plan"
"""
        if update.message:
            await update.message.reply_text(welcome_message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages using the simple agent"""
        try:
            if not update.effective_user or not update.message or not update.effective_chat:
                return
                
            user_id = update.effective_user.id
            message_text = update.message.text
            
            if not message_text:
                return
            
            logger.info(f"🧠 SIMPLE BOT: Processing message from user {user_id}: {message_text}")
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get response from simple agent
            response = await self.agent.chat(user_id, message_text)
            
            # Send response
            await update.message.reply_text(response)
            
            logger.info(f"✅ SIMPLE BOT: Sent response to user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ SIMPLE BOT: Error handling message: {str(e)}")
            if update.message:
                await update.message.reply_text(
                    "I encountered an error processing your message. Please try again."
                )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"❌ SIMPLE BOT: Error occurred: {context.error}")
    
    def run(self):
        """Start the bot"""
        if not self.bot_token:
            raise ValueError("Bot token is required")
            
        print("🧠 Simple Planning Bot - Trust-Based Agent")
        print("=" * 50)
        print("🚀 Starting simple bot...")
        print("💡 This bot uses natural LLM intelligence instead of rigid rules")
        print("📱 Test it in Telegram to compare with the complex agent")
        print()
        
        # Create application
        application = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_error_handler(self.error_handler)
        
        # Start polling
        logger.info("🚀 Simple bot started in polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        bot = SimpleTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Simple bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting simple bot: {e}")
        sys.exit(1)
