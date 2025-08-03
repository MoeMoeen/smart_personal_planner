#!/usr/bin/env python3
"""
Test refinement workflow specifically
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

def test_refinement_workflow():
    """Test the plan refinement workflow"""
    print("🔄 Testing Plan Refinement Workflow...")
    
    from app.agent.graph import run_graph_with_message
    
    # First, let's check what plans exist
    print("\n1️⃣ Checking existing plans...")
    result1 = run_graph_with_message("Show me my plans", user_id=1)
    
    if result1["messages"]:
        final_message = result1["messages"][-1]
        print(f"🗂️ Existing plans: {str(final_message.content)[:300]}...")
    
    # Test plan refinement request
    print("\n2️⃣ Testing plan refinement...")
    refinement_request = "Can you refine my vacation savings plan to be less aggressive and more realistic?"
    
    result2 = run_graph_with_message(refinement_request, user_id=1)
    
    print(f"✅ Intent: {result2.get('intent', 'Unknown')}")
    print(f"📊 Messages: {len(result2['messages'])}")
    
    if result2["messages"]:
        final_message = result2["messages"][-1]
        print(f"🤖 Refinement response: {str(final_message.content)[:400]}...")

def test_complex_conversation():
    """Test multi-turn complex conversation"""
    print("\n🧠 Testing Complex Multi-Turn Conversation...")
    
    from app.agent.graph import run_graph_with_message
    
    test_cases = [
        "I want to learn Python programming in 6 months",
        "What's the difference between project goals and habit goals in your system?",
        "Can you show me my approved plans?",
        "I want to create a habit of reading 30 minutes daily"
    ]
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n🧪 Complex Test {i}: {user_input[:50]}...")
        
        try:
            result = run_graph_with_message(user_input, user_id=1)
            print(f"   ✅ Intent: {result.get('intent', 'Unknown')}")
            print(f"   📊 Steps: {len(result['messages'])}")
            
            # Show brief response
            if result["messages"]:
                final_message = result["messages"][-1]
                response_preview = str(final_message.content)[:150]
                print(f"   🤖 Response: {response_preview}...")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting advanced testing...")
    
    # Test refinement workflow
    test_refinement_workflow()
    
    # Test complex conversations
    test_complex_conversation()
    
    print("\n🎉 Advanced testing completed!")
