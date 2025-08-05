"""
Simple, Trust-Based LLM Agent - Prototype
==========================================

This is a prototype of a much simpler approach that trusts the LLM's natural intelligence
instead of constraining it with complex multi-agent workflows.

Key Philosophy:
- Trust the LLM to understand context naturally
- Minimal explicit instructions
- Let the LLM decide when and how to use tools
- Focus on natural conversation flow
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, BaseMessage
from app.agent.tools import all_tools
from app.agent.conversation_manager import ConversationManager
from datetime import date
import logging
from typing import List

logger = logging.getLogger(__name__)

class SimplePlanningAgent:
    """
    A much simpler agent that trusts LLM intelligence instead of constraining it.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            timeout=60
        )
        
        # Bind tools directly to the LLM - let it decide when to use them
        self.llm_with_tools = self.llm.bind_tools(all_tools)
        
        self.conversation_manager = ConversationManager()
    
    def get_simple_system_prompt(self) -> str:
        """
        Much shorter, trust-based system prompt that lets the LLM be naturally intelligent.
        """
        today = date.today().isoformat()
        
        return f"""You are an intelligent personal planning assistant. Today is {today}.

**Your Role:**
Help users create, manage, and achieve their personal goals through smart planning.

**Available Tools:**
You have access to planning tools - use them when they make sense:
- generate_plan_with_ai_tool: Create new comprehensive plans
- get_plan_details_smart: Show plan details (use without plan_id for latest plan)
- get_user_plans: List all user plans
- refine_existing_plan: Improve existing plans
- get_user_approved_plans: Show approved plans

**Your Intelligence:**
- Be naturally conversational and context-aware
- Use your judgment about when tools are needed
- Remember what just happened in the conversation
- Distinguish between creating new plans vs discussing existing ones
- Be helpful, insightful, and encouraging

**Trust Your Instincts:**
- If someone just described a goal, they probably want a plan created
- If they ask about "the plan you just made" or "my latest plan", show them details
- If they're asking questions about a plan, have a natural conversation
- If they want book recommendations or advice, just give great advice

Be smart. Be helpful. Trust yourself."""

    async def chat(self, user_id: int, message: str) -> str:
        """
        Simple chat method that lets the LLM handle the conversation naturally.
        """
        try:
            logger.info(f"🧠 SIMPLE AGENT: Processing message for user {user_id}")
            
            # Get conversation history
            history = self.conversation_manager.get_conversation_history(user_id)
            
            # Build message chain
            messages: List[BaseMessage] = [SystemMessage(content=self.get_simple_system_prompt())]
            
            # Add conversation history
            for msg in history:
                messages.append(msg)
            
            # Add current user message
            messages.append(HumanMessage(content=message))
            
            logger.info(f"🧠 SIMPLE AGENT: Invoking LLM with {len(messages)} messages")
            
            # Let the LLM naturally decide what to do
            response = self.llm_with_tools.invoke(messages)
            
            # Handle tool calls if the LLM decided to use them
            tool_calls = getattr(response, 'tool_calls', None)
            if tool_calls:
                logger.info(f"🔧 SIMPLE AGENT: LLM chose to use {len(tool_calls)} tools")
                
                # Execute tools
                messages.append(response)
                
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"🔧 SIMPLE AGENT: Executing {tool_name} with args: {tool_args}")
                    
                    # Find and execute the tool
                    tool_result = None
                    for tool in all_tools:
                        if tool.name == tool_name:
                            tool_result = tool.invoke(tool_args)
                            break
                    
                    if tool_result:
                        messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call["id"]
                        ))
                
                # Get final response with tool results
                final_response = self.llm_with_tools.invoke(messages)
                response_text = getattr(final_response, 'content', str(final_response))
            else:
                logger.info("🧠 SIMPLE AGENT: LLM responded without tools")
                response_text = getattr(response, 'content', str(response))
            
            # Save conversation
            self.conversation_manager.add_messages(user_id, [
                HumanMessage(content=message),
                AIMessage(content=response_text)
            ])
            
            logger.info(f"✅ SIMPLE AGENT: Generated {len(response_text)} character response")
            return response_text
            
        except Exception as e:
            logger.error(f"❌ SIMPLE AGENT: Error processing message: {str(e)}")
            return f"I encountered an error: {str(e)}. Please try again."

# Simple function to test the agent
async def test_simple_agent():
    """
    Quick test function to compare with the complex agent.
    """
    agent = SimplePlanningAgent()
    
    # Test conversation
    print("=== SIMPLE AGENT TEST ===")
    
    response1 = await agent.chat(1, "I want to read 2 geopolitical books per month")
    print(f"User: I want to read 2 geopolitical books per month")
    print(f"Agent: {response1}")
    print()
    
    response2 = await agent.chat(1, "Give me full plan details")
    print(f"User: Give me full plan details")
    print(f"Agent: {response2}")
    print()
    
    response3 = await agent.chat(1, "How many cycles will this have?")
    print(f"User: How many cycles will this have?")
    print(f"Agent: {response3}")
    print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_simple_agent())
