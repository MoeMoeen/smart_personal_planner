#!/usr/bin/env python3
"""
Quick test for plan management without loops
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_single_goal():
    """Test a single plan creation"""
    print("🧪 Testing single plan creation...")
    
    from app.agent.graph import run_graph_with_message
    
    user_input = "I want to read 12 books this year"
    
    print(f"🎯 Testing: {user_input}")
    
    try:
        result = run_graph_with_message(user_input, user_id=1)
        
        print(f"✅ Intent: {result.get('intent', 'Unknown')}")
        print(f"📊 Messages: {len(result['messages'])}")
        
        # Show the final response
        if result["messages"]:
            final_message = result["messages"][-1]
            final_content = str(final_message.content)
            print(f"🤖 Final response: {final_content[:300]}...")
        
        print("✅ Plan creation test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Error in plan creation test")

if __name__ == "__main__":
    print("🚀 Testing plan creation fix...")
    test_single_goal()
    print("🎉 Test completed!")
