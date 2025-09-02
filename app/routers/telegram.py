# app/routers/telegram.py

import logging
import os
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio
from datetime import datetime

from app.agent.graph import run_graph_with_message  # Our LangGraph workflow (Complex Agent)
from app.agent.agent_factory import AgentFactory  # Alternative agent factory
from app.db import SessionLocal
from app.models import User
from sqlalchemy.orm import Session
from app.orchestration.message_handler import handle_user_message


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Global variable to store the Telegram application
telegram_app: Optional[Application] = None

class TelegramWebhook(BaseModel):
    """Pydantic model for incoming Telegram webhooks"""
    update_id: int
    message: Optional[dict] = None

def get_or_create_user(telegram_user_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> int:
    """Get or create a user based on Telegram user ID"""
    db = SessionLocal()
    try:
        # Look for existing user by telegram_user_id (assuming you have this field)
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        
        if not user:
            # Create new user
            user = User(
                telegram_user_id=telegram_user_id,
                username=username or f"user_{telegram_user_id}",
                first_name=first_name or "User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user with ID {user.id} for Telegram user {telegram_user_id}")
        
        return user.id  # type: ignore
    except Exception as e:
        logger.error(f"Error getting or creating user: {e}")
        db.rollback()
        # Return a default user ID for now (you might want to handle this differently)
        return 1
    finally:
        db.close()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    if not update.message:
        return
        
    user = update.effective_user
    if not user:
        await update.message.reply_text("Sorry, I couldn't identify you. Please try again.")
        return
        
    welcome_message = f"""
🎯 **Welcome to Smart Personal Planner!** 

Hi {user.first_name or 'there'}! I'm your AI-powered goal planning assistant.

**What I can do:**
• 📝 Create structured plans from your goals
• 🎯 Break down projects into actionable tasks  
• 🔄 Set up recurring habits with schedules
• 📊 Track your progress over time
• 🔧 Refine plans based on your feedback

**How to use me:**
Just tell me your goal in natural language! For example:
• "I want to read 12 books this year"
• "I want to exercise 3 times per week"
• "I want to learn Spanish in 6 months"
• "I want to build a mobile app"

Try it now! What goal would you like to work on? 🚀
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    if not update.message:
        return
        
    help_text = """
🆘 **Smart Personal Planner - Help**

**Commands:**
• `/start` - Get started with the bot
• `/help` - Show this help message
• `/status` - Check your recent goals
• `/examples` - See example goals

**How to create goals:**
Just describe what you want to achieve! I'll understand and create a structured plan.

**Examples:**
• "I want to get fit and lose 10 pounds"
• "I want to learn Python programming"  
• "I want to meditate daily for 10 minutes"
• "I want to save $5000 for vacation"

**Need more help?** Just ask me anything about goal planning! 💪
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show example goals"""
    if not update.message:
        return
        
    examples_text = """
💡 **Example Goals You Can Try:**

**📚 Learning Goals:**
• "I want to learn Spanish and be conversational in 6 months"
• "I want to read 24 books this year"
• "I want to master Python programming"

**💪 Health & Fitness:**
• "I want to run a 5K race in 3 months"
• "I want to go to the gym 4 times per week"
• "I want to drink 8 glasses of water daily"

**💰 Financial Goals:**
• "I want to save $10,000 for a house down payment"
• "I want to invest $500 monthly in index funds"

**🎨 Creative Projects:**
• "I want to write a novel in 12 months"
• "I want to build a mobile app"
• "I want to start a YouTube channel"

**🏠 Personal Development:**
• "I want to meditate 15 minutes every morning"
• "I want to organize and declutter my entire home"

Try one of these or create your own! 🎯
    """
    await update.message.reply_text(examples_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's recent goals"""
    if not update.message or not update.effective_user:
        return
        
    telegram_user_id = update.effective_user.id
    user_id = get_or_create_user(telegram_user_id, update.effective_user.username, update.effective_user.first_name)
    
    # TODO: Implement getting user's recent goals from database
    status_text = f"""
📊 **Your Goal Status**

User ID: {user_id}
Telegram ID: {telegram_user_id}

Feature coming soon! 🚧
I'll show your recent goals and progress here.

For now, just tell me a new goal and I'll help you plan it! 🎯
    """
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages - this is where the magic happens!"""
    try:
        if not update.message or not update.message.text or not update.effective_user or not update.effective_chat:
            return
            
        user_message = update.message.text
        telegram_user = update.effective_user
        
        # Get or create user in our database
        user_id = get_or_create_user(
            telegram_user.id,
            telegram_user.username,
            telegram_user.first_name
        )
        
        logger.info(f"Processing message from user {user_id} (Telegram: {telegram_user.id}): '{user_message}'")
        
        # Send "typing" action to show bot is processing
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # 🤖 CENTRALIZED AGENT SYSTEM - Defaults to Complex LangGraph
        # Environment variable AGENT_TYPE=simple can switch to simple agent
        try:
            #result = run_graph_with_message(user_message, user_id)  # Uses complex agent by default
            
            # New Cognitive AI Based Implementation
            
            memory_context = {}  # TODO: fetch from DB
            response_text = await handle_user_message(user_id, user_message, memory_context)
            await update.message.reply_text(response_text, parse_mode='Markdown')
            

            # Extract the final response from the LangGraph result
            if result and "messages" in result and len(result["messages"]) > 0:
                final_message = result["messages"][-1]
                intent = result.get("intent", "unknown")
                
                # Check if this was a plan management or conversational response
                if intent == "plan_management":
                    # This was plan management - extract detailed plan information
                    response_text = str(final_message.content)
                    
                    # Try to extract plan details from the tool messages
                    plan_details = None
                    for msg in result["messages"]:
                        if hasattr(msg, 'type') and msg.type == "tool":
                            try:
                                import json
                                tool_data = json.loads(str(msg.content))
                                if "plan_title" in tool_data:
                                    plan_details = tool_data
                                    break
                            except:
                                pass
                    
                    # Format detailed response
                    if plan_details:
                        goal_type_emoji = "🎯" if plan_details.get("goal_type") == "project" else "🔄"
                        formatted_response = f"""
{goal_type_emoji} **Plan Successfully Created!**

**📝 Title:** {plan_details.get('plan_title', 'Your Goal')}
**📋 Type:** {plan_details.get('goal_type', 'Unknown').title()}
**📖 Description:** {plan_details.get('goal_description', 'No description')}
**📅 Timeline:** {plan_details.get('timeline', 'Not specified')}

**📋 Plan Details:**
{plan_details.get('tasks_info', 'No details available')}

💡 **What's next?**
• Start working on your first tasks
• Track your progress regularly  
• Let me know if you need any adjustments!

📝 Want to create another plan or have questions? Just ask!
                        """.strip()
                    else:
                        # Fallback to generic response if can't extract details
                        formatted_response = f"""
🎯 **Plan Successfully Created!**

{response_text}

💡 **What's next?**
• Review your plan in detail
• Start working on the first tasks
• Let me know if you need any adjustments!

📝 Want to create another plan? Just tell me what you'd like to achieve! 
                        """.strip()
                else:
                    # This was a conversational response - use it directly
                    formatted_response = str(final_message.content)
                
                # Send the appropriate response
                await update.message.reply_text(formatted_response, parse_mode='Markdown')
                
            else:
                await update.message.reply_text(
                    "❌ Sorry, I had trouble processing your message. Please try again or rephrase your request.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error running LangGraph workflow: {e}")
            await update.message.reply_text(
                f"❌ **Error:** I encountered an issue while processing your request: {str(e)[:200]}...\n\nPlease try again with a different message.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        if update.message:
            await update.message.reply_text(
                "❌ Sorry, I'm having technical difficulties. Please try again in a moment.",
                parse_mode='Markdown'
            )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def setup_telegram_app() -> Application:
    """Setup and configure the Telegram application"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("examples", examples_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Handle all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    return application

@router.post("/webhook")
async def telegram_webhook(webhook_data: dict):
    """Handle incoming Telegram webhooks"""
    global telegram_app
    
    if not telegram_app:
        telegram_app = setup_telegram_app()
    
    try:
        # Create Update object from webhook data
        update = Update.de_json(webhook_data, telegram_app.bot)
        
        # Process the update
        await telegram_app.process_update(update)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/set-webhook")
async def set_webhook():
    """Set the webhook URL for the Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")  # e.g., "https://yourdomain.com/telegram/webhook"
    
    if not token or not webhook_url:
        raise HTTPException(
            status_code=400, 
            detail="TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL environment variables are required"
        )
    
    try:
        app = setup_telegram_app()
        await app.bot.set_webhook(url=webhook_url)
        return {"status": "webhook set", "url": webhook_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhook-info")
async def get_webhook_info():
    """Get current webhook information"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN is required")
    
    try:
        app = setup_telegram_app()
        webhook_info = await app.bot.get_webhook_info()
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# For local development/testing - polling mode
async def run_telegram_polling():
    """Run Telegram bot in polling mode for local development"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    application = setup_telegram_app()
    
    logger.info("Starting Telegram bot in polling mode...")
    await application.initialize()
    await application.start()
    
    # Check if updater exists before using it
    if application.updater:
        await application.updater.start_polling()
        
        try:
            # Keep the bot running
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Stopping Telegram bot...")
        finally:
            await application.updater.stop()
    else:
        logger.error("Application updater is not available")
    
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    # For testing - run the bot in polling mode
    asyncio.run(run_telegram_polling())
