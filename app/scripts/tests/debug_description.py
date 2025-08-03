"""
Debug the description field issue by checking what the AI actually generates
"""
import os
from dotenv import load_dotenv
from app.ai.goal_parser_chain import goal_parser_chain
from datetime import date
import json

# Load environment variables
load_dotenv()

test_goal = "I want to read 12 books this year"

print("🔍 Debugging description field issue...")
print("=" * 50)

try:
    today_date = date.today().isoformat()
    
    # The chain returns a dict with "plan" key
    result_dict = goal_parser_chain.invoke({
        "goal_description": test_goal,
        "today_date": today_date
    })
    result = result_dict["plan"]
    
    print(f"Input: '{test_goal}'")
    print("\n📝 Generated Plan Structure:")
    print(f"Goal Title: {result.goal.title}")
    print(f"Goal Description: '{result.goal.description}'")
    print(f"Goal Type: {result.goal.goal_type}")
    print(f"Start Date: {result.goal.start_date}")
    print(f"End Date: {result.goal.end_date}")
    
    # Check if description is actually present and not empty
    if not result.goal.description or result.goal.description.strip() == "":
        print("❌ ISSUE: Description is empty or None!")
    else:
        print(f"✅ Description present: {len(result.goal.description)} characters")
        
    # Show the full goal object
    print("\n🔧 Raw Goal Object:")
    goal_dict = result.goal.dict()
    print(json.dumps(goal_dict, indent=2, default=str))
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(f"Stack trace: {traceback.format_exc()}")

print("\n" + "=" * 50)
