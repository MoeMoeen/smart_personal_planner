# app/agent/conversation_manager.py

from typing import Dict, List, Optional
import logging
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages persistent conversation history across graph executions"""
    
    def __init__(self, max_messages_per_user: int = 50):
        """Initialize conversation manager
        
        Args:
            max_messages_per_user: Maximum messages to store per user (default: 50)
        """
        self.conversations: Dict[int, List[BaseMessage]] = {}
        self.max_messages_per_user = max_messages_per_user
        logger.info(f"🧠 CONVERSATION MANAGER: Initialized with max {max_messages_per_user} messages per user")
    
    def add_messages(self, user_id: int, messages: List[BaseMessage]):
        """Add new messages to user's conversation history"""
        logger.info(f"💾 CONVERSATION: Adding {len(messages)} messages for user {user_id}")
        
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        # ✅ SOLUTION: Filter messages to avoid OpenAI API validation issues
        # Only store HumanMessage and AIMessage without tool_calls
        safe_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                safe_messages.append(msg)
            elif isinstance(msg, AIMessage):
                # Only include AIMessages that don't have tool_calls
                if not hasattr(msg, 'tool_calls') or not msg.tool_calls:
                    safe_messages.append(msg)
                # Skip AIMessages with tool_calls to avoid OpenAI validation errors
        
        if safe_messages:
            self.conversations[user_id].extend(safe_messages)
            
            # Cleanup if too many messages
            if len(self.conversations[user_id]) > self.max_messages_per_user:
                excess = len(self.conversations[user_id]) - self.max_messages_per_user
                self.conversations[user_id] = self.conversations[user_id][excess:]
                logger.info(f"🗑️ CONVERSATION: Cleaned up {excess} old messages for user {user_id}")
            
            logger.info(f"💾 CONVERSATION: Added {len(safe_messages)} safe messages for user {user_id}. Total: {len(self.conversations[user_id])}")
        else:
            logger.info(f"⚠️ CONVERSATION: No safe messages to add for user {user_id}")
    
    def get_conversation_history(self, user_id: int, max_recent_messages: int = 10) -> List[BaseMessage]:
        """Get recent conversation history for a user"""
        if user_id not in self.conversations:
            return []
        
        # Get recent messages
        recent_messages = self.conversations[user_id][-max_recent_messages:] if max_recent_messages else self.conversations[user_id]
        
        logger.info(f"📖 CONVERSATION: Retrieved {len(recent_messages)} messages for user {user_id}")
        return recent_messages
    
    def clear_conversation(self, user_id: int):
        """Clear conversation history for a user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"🗑️ CONVERSATION: Cleared history for user {user_id}")
        else:
            logger.info(f"ℹ️ CONVERSATION: No history to clear for user {user_id}")
    
    def get_conversation_count(self, user_id: int) -> int:
        """Get the number of messages for a user"""
        return len(self.conversations.get(user_id, []))
    
    def get_all_users(self) -> List[int]:
        """Get list of all users with conversation history"""
        return list(self.conversations.keys())

# Global conversation manager instance
conversation_manager = ConversationManager()
