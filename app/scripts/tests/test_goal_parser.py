#!/usr/bin/env python3
# Quick test to isolate the goal_parser_chain issue

import sys
import os
sys.path.append('/home/moemoeen/Documents/GitHub/Python_Projects_Personal/smart_personal_planner')

from app.ai.goal_parser_chain import goal_parser_chain, parser
from datetime import date

def test_goal_parser_chain():
    print("🧪 Testing goal_parser_chain directly...")
    
    try:
        today = date.today().isoformat()
        print(f"📅 Today: {today}")
        
        input_data = {
            "goal_description": "I want to read 12 books this year",
            "format_instructions": parser.get_format_instructions(),
            "today_date": today
        }
        
        print(f"📝 Input: {input_data}")
        print("⚡ Invoking goal_parser_chain...")
        
        result = goal_parser_chain.invoke(input_data)
        print(f"✅ Raw result type: {type(result)}")
        print(f"📊 Raw result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and "plan" in result:
            plan = result["plan"]
            print(f"✅ Plan extracted: {type(plan)}")
            print(f"📋 Plan title: {getattr(plan.goal, 'title', 'No title')}")
        else:
            print(f"❌ Unexpected result structure: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_goal_parser_chain()
