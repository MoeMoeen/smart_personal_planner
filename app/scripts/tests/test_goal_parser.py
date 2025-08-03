"""
Test script to verify goal_parser_chain output format fixes
"""
import os
from dotenv import load_dotenv
from app.ai.goal_parser_chain import goal_parser_chain

# Load environment variables
load_dotenv()

# Test cases for different goal types
test_goals = [
    "I want to read 12 books this year",
    "I want to go to the gym every morning at 6 AM", 
    "I want to learn Python programming and build 3 projects",
    "I want to drink 8 glasses of water daily",
    "I want to save $10,000 for a vacation",
    "I want to meditate for 10 minutes every evening"
]

print("Testing goal_parser_chain with improved classification...")
print("=" * 60)

for i, goal in enumerate(test_goals, 1):
    print(f"\nTest {i}: '{goal}'")
    print("-" * 40)
    
    try:
        from datetime import date
        today_date = date.today().isoformat()
        
        # The chain returns a dict with "plan" key
        result_dict = goal_parser_chain.invoke({
            "goal_description": goal,
            "today_date": today_date
        })
        result = result_dict["plan"]
        
        # Check if we have the expected fields
        goal = result.goal  # Access the nested goal object
        print(f"Title: {goal.title}")
        print(f"Description: {getattr(goal, 'description', 'MISSING!')}")
        print(f"Goal Type: {getattr(goal, 'goal_type', 'MISSING!')}")
        print(f"Timeline: {goal.start_date} to {goal.end_date}")
        print(f"Progress: {goal.progress}%")
        
        # Validate goal_type is either 'project' or 'habit'
        goal_type = getattr(goal, 'goal_type', None)
        if goal_type not in ['project', 'habit']:
            print(f"⚠️  WARNING: Invalid goal_type '{goal_type}' - should be 'project' or 'habit'")
        else:
            print(f"✅ Valid goal_type: {goal_type}")
            
        # Show structure based on goal type
        if goal_type == 'habit' and goal.habit_cycles:
            print(f"📅 Habit cycles: {len(goal.habit_cycles)}")
            print(f"🔄 Frequency: {goal.goal_frequency_per_cycle} times per {goal.recurrence_cycle}")
        elif goal_type == 'project' and goal.tasks:
            print(f"📋 Tasks: {len(goal.tasks)}")
            
        print(f"📊 Plan ID: {result.plan_id}, Refinement: {result.refinement_round}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
print("\n" + "=" * 60)
print("Testing complete!")
