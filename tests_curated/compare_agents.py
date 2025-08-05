#!/usr/bin/env python3
"""
Agent Comparison Test
====================

Test both the complex multi-agent system and the simple trust-based agent
to compare their intelligence and behavior.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.agent.simple_agent import SimplePlanningAgent
from app.agent.graph import run_graph_with_message


async def test_conversation_flow():
    """
    Test the same conversation with both agents to compare behavior.
    """
    
    print("🧪 AGENT COMPARISON TEST")
    print("=" * 50)
    
    # Initialize simple agent
    simple_agent = SimplePlanningAgent()
    
    # Test conversation sequence - Basic scenario
    basic_test_messages = [
        "I want to read 2 geopolitical books per month",
        "Give me full plan details", 
        "How many cycles will this have?",
        "Can you suggest some good geopolitics books?"
    ]
    
    # Complex scenarios to test intelligence and context handling
    complex_test_messages = [
        "I want to learn machine learning and also improve my fitness. Can you help me create comprehensive plans for both?",
        "Show me the detailed breakdown of all my current goals and their schedules",
        "I think the ML plan is too ambitious. Can you refine it to be more beginner-friendly?",
        "Actually, approve the fitness plan as it looks good to me",
        "Give me a weekly schedule that shows when I should do ML vs fitness activities",
        "Can you suggest some good books for machine learning beginners?",
        "What if I want to focus on ML for 3 months, then switch focus to fitness for 2 months? Create a new plan for this approach",
        "Show me all my current plans and their approval status"
    ]
    
    user_id = 999  # Test user ID
    
    # Run basic scenario first
    print("\n🟢 BASIC SCENARIO TEST")
    print("=" * 60)
    
    for i, message in enumerate(basic_test_messages, 1):
        print(f"\n{'='*60}")
        print(f"BASIC TEST {i}: {message}")
        print(f"{'='*60}")
        
        # Test Complex Agent (Current System)
        print(f"\n🤖 COMPLEX AGENT:")
        print("-" * 50)
        try:
            complex_response = run_graph_with_message(message, user_id)
            print(complex_response)
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Test Simple Agent (Trust-Based Prototype)
        print(f"\n🧠 SIMPLE AGENT:")
        print("-" * 50)
        try:
            simple_response = await simple_agent.chat(user_id, message)
            print(simple_response)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n🔥 COMPLEX SCENARIO TEST")
    print("=" * 60)
    print("Testing multi-goal management, context switching, plan refinement, and complex reasoning...")
    
    # Reset user state for complex scenario
    user_id = 888  # Different user for complex scenario
    
    for i, message in enumerate(complex_test_messages, 1):
        print(f"\n{'='*60}")
        print(f"COMPLEX TEST {i}: {message}")
        print(f"{'='*60}")
        
        # Test Complex Agent (Current System)
        print(f"\n🤖 COMPLEX AGENT:")
        print("-" * 50)
        try:
            complex_response = run_graph_with_message(message, user_id)
            print(complex_response)
        except Exception as e:
            print(f"ERROR: {e}")
        
        # Test Simple Agent (Trust-Based Prototype)
        print(f"\n🧠 SIMPLE AGENT:")
        print("-" * 50)
        try:
            simple_response = await simple_agent.chat(user_id, message)
            print(simple_response)
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n{'='*60}")
    print("🎯 COMPREHENSIVE COMPARISON COMPLETE")
    print(f"{'='*60}")
    
    print("""
🔍 INTELLIGENCE ANALYSIS:

📊 BASIC SCENARIOS:
1. Which agent handles simple plan creation better?
2. Which provides clearer plan details?
3. Which gives more natural responses?

🧠 COMPLEX SCENARIOS:
1. Which agent handles multi-goal management better?
2. Which maintains context across complex conversations?
3. Which handles plan modifications and refinements more intelligently?
4. Which better understands nuanced requests (time constraints, priority changes)?
5. Which feels more like an intelligent assistant vs a programmed bot?

🎯 OVERALL ASSESSMENT:
- Natural conversation flow
- Context awareness and memory
- Tool usage intelligence
- Response quality and helpfulness
- Human-like reasoning ability
- Error handling and graceful degradation

🚀 WHICH APPROACH DEMONSTRATES SUPERIOR INTELLIGENCE?
    """)

if __name__ == "__main__":
    asyncio.run(test_conversation_flow())
