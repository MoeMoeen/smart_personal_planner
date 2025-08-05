#!/usr/bin/env python3
"""
Test script for the enhanced intelligent Telegram bot
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_graph_directly():
    """Test the LangGraph workflow directly"""
    print("🧪 Testing LangGraph workflow directly...")
    
    from app.agent.graph import run_graph_with_message
    
    test_cases = [
        ("Hey", "greeting"),
        ("Hello how are you?", "greeting"),
        ("I want to save $5000 for vacation", "plan_management"),
        ("Can you elaborate more what you mean by Review and adjust budget monthly?", "clarification"),
        ("What is a project goal?", "question"),
        ("How do habit goals work?", "question"),
        ("I want to exercise 3 times per week", "plan_management")
    ]
    
    for i, (user_input, expected_intent) in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST CASE {i}: {user_input}")
        print(f"Expected intent: {expected_intent}")
        print(f"{'='*60}")
        
        try:
            result = run_graph_with_message(user_input, user_id=1)
            
            print(f"✅ Intent classified as: {result.get('intent', 'Unknown')}")
            print(f"📊 Total messages: {len(result['messages'])}")
            
            # Show the final response
            if result["messages"]:
                final_message = result["messages"][-1]
                final_content = str(final_message.content)
                print(f"🤖 Final response ({len(final_content)} chars):")
                print(f"   {final_content[:200]}{'...' if len(final_content) > 200 else ''}")
            
            print(f"✅ Test case {i} completed successfully!")
            
        except Exception as e:
            print(f"❌ Test case {i} failed: {e}")
            logger.exception(f"Error in test case {i}")

if __name__ == "__main__":
    print("🚀 Starting intelligent bot testing...")
    
    # Test the graph workflow
    test_graph_directly()
    
    print("\n🎉 Testing completed!")
