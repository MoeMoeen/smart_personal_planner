"""
Test the complete LangGraph workflow with improved goal parsing
"""
import os
from dotenv import load_dotenv
from app.agent.graph import run_graph_with_message

# Load environment variables
load_dotenv()

test_messages = [
    "I want to read 12 books this year",
    "I want to exercise 3 times per week",
    "I want to learn Spanish and be conversational in 6 months"
]

user_id = 1  # Test user

print("Testing complete LangGraph workflow with improved parsing...")
print("=" * 70)

for i, message in enumerate(test_messages, 1):
    print(f"\n🎯 Test {i}: '{message}'")
    print("-" * 50)
    
    try:
        result = run_graph_with_message(message, user_id)
        
        print(f"✅ Result: {result['messages'][-1].content}")
        
        # Extract goal_id from result if present
        if "goal_id=" in result['messages'][-1].content:
            goal_id = result['messages'][-1].content.split("goal_id=")[1].split(")")[0]
            print(f"🆔 Created goal with ID: {goal_id}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        
print("\n" + "=" * 70)
print("LangGraph testing complete!")
