# app/agent/simple_agent_backup.py
"""
PRESERVED: Simple Trust-Based Agent Architecture
===============================================

This file preserves the simple trust-based agent approach for future reference.
The simple agent bypasses complex graph structures and directly integrates with
the backend using enhanced LangChain tools.

Key Features:
- Direct backend integration
- Trust-based approach (assumes LLM will use tools correctly)
- Enhanced tools with robust parsing
- Minimal complexity, maximum efficiency

Usage Example:
    from app.agent.simple_agent_backup import run_simple_agent
    result = run_simple_agent("I want to read 2 books per month", user_id=1)
"""

import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from pydantic import SecretStr

# Import the enhanced tools
from app.agent.tools import (
    generate_plan_with_ai_tool,
    get_user_plans,
    get_plan_details_smart,
    get_user_approved_plans,
    plan_feedback_tool
)

def create_simple_agent() -> AgentExecutor:
    """
    Creates the simple trust-based agent with enhanced tools.
    
    This agent relies on the LLM's intelligence to choose the right tools
    and trusts it to provide good responses without complex orchestration.
    """
    
    # Initialize the LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
        
    llm = ChatOpenAI(
        model="gpt-4-0613",
        temperature=0.1,
        api_key=SecretStr(api_key)
    )
    
    # Define the system prompt for trust-based approach
    system_prompt = """You are an intelligent personal planning assistant with access to powerful tools.

Your capabilities:
- Create comprehensive plans (habits and projects) using generate_plan_with_ai
- Retrieve user plans with get_user_plans
- Get detailed plan information with get_plan_details_smart
- Handle plan feedback and refinement with plan_feedback
- Show approved plans with get_user_approved_plans

Instructions:
1. Always use the most appropriate tool for the user's request
2. Provide detailed, helpful responses with clear structure
3. For plan creation, use generate_plan_with_ai with the user's exact request
4. For plan details, use get_plan_details_smart (it's intelligent and finds the right plan)
5. For refinement requests, use plan_feedback with action='refine'
6. Be conversational but informative

Trust your intelligence to choose the right approach for each user request."""

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create the tools list
    tools = [
        generate_plan_with_ai_tool,
        get_user_plans,
        get_plan_details_smart,
        get_user_approved_plans,
        plan_feedback_tool
    ]
    
    # Create the agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3
    )
    
    return agent_executor

def run_simple_agent(message: str, user_id: int) -> Dict[str, Any]:
    """
    Run the simple trust-based agent with a user message.
    
    Args:
        message: User's input message
        user_id: User ID for plan operations
        
    Returns:
        Dict containing the agent's response and metadata
    """
    try:
        # Create the agent
        agent_executor = create_simple_agent()
        
        # Prepare the input
        agent_input = {
            "input": message,
            "chat_history": [],  # Could be enhanced with actual chat history
            "user_id": user_id  # Pass user_id for tool context
        }
        
        # Execute the agent
        result = agent_executor.invoke(agent_input)
        
        return {
            "response": result.get("output", ""),
            "success": True,
            "agent_type": "simple_trust_based",
            "message": message,
            "user_id": user_id
        }
        
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "success": False,
            "agent_type": "simple_trust_based",
            "message": message,
            "user_id": user_id,
            "error": str(e)
        }

# Example usage and testing
if __name__ == "__main__":
    # Test the simple agent
    test_cases = [
        "I want to read 2 geopolitical books per month",
        "Show me my plan details",
        "Can you refine my reading plan to be more realistic?"
    ]
    
    for test_message in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing: {test_message}")
        print(f"{'='*50}")
        
        result = run_simple_agent(test_message, user_id=1)
        print(f"Success: {result['success']}")
        print(f"Response: {result['response'][:200]}...")
