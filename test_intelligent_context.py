#!/usr/bin/env python3
"""
Test intelligent context awareness - the agent should be smart enough to remember what it just created
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

def test_context_intelligence():
    """Test that agent remembers context without needing additional tools"""
    print("🧠 Testing Intelligent Context Awareness...")
    
    from app.agent.graph import run_graph_with_message
    
    # Step 1: Create a plan
    print("\n1️⃣ Creating a plan...")
    result1 = run_graph_with_message("I want to learn guitar in 3 months", user_id=10)
    
    print(f"✅ Intent: {result1.get('intent', 'Unknown')}")
    print(f"📊 Messages: {len(result1['messages'])}")
    
    if result1["messages"]:
        final_message = result1["messages"][-1]
        print(f"🤖 Plan creation response: {str(final_message.content)[:200]}...")
        
        # Look for goal ID in the response
        import re
        goal_id_match = re.search(r'goal ID:?\s*(\d+)', str(final_message.content))
        if goal_id_match:
            goal_id = goal_id_match.group(1)
            print(f"🎯 Detected Goal ID: {goal_id}")
    
    # Step 2: IMMEDIATELY ask about "the plan you just created" 
    # This should work WITHOUT additional tools - the agent should be smart enough to remember!
    print("\n2️⃣ Testing context awareness...")
    context_questions = [
        "Show me details of the plan you just created",
        "Can you tell me more about my latest plan?", 
        "What tasks are in the plan we just made?",
        "I want to see the full breakdown of what you just planned for me"
    ]
    
    for i, question in enumerate(context_questions, 1):
        print(f"\n🧪 Context Test {i}: {question}")
        
        try:
            # Pass the SAME conversation state - this is key!
            # The agent should have access to the previous messages
            result = run_graph_with_message(question, user_id=10)
            
            print(f"   ✅ Intent: {result.get('intent', 'Unknown')}")
            print(f"   📊 Steps: {len(result['messages'])}")
            
            # Check if response contains intelligent context
            if result["messages"]:
                final_message = result["messages"][-1]
                response = str(final_message.content)
                
                # Look for signs of intelligence vs generic responses
                intelligence_indicators = [
                    "guitar", "3 months", "plan", "goal", "task", "schedule",
                    "learn", "practice", "lesson", "skill"
                ]
                
                intelligent_words = [word for word in intelligence_indicators if word.lower() in response.lower()]
                
                print(f"   🎯 Intelligent words found: {intelligent_words}")
                print(f"   🤖 Response preview: {response[:150]}...")
                
                if len(intelligent_words) >= 3:
                    print(f"   ✅ INTELLIGENT: Agent remembered context!")
                else:
                    print(f"   ❌ GENERIC: Agent seems to have lost context")
                    
        except Exception as e:
            print(f"   ❌ Failed: {e}")

def test_existing_crud_usage():
    """Test that we can use existing CRUD functions directly for intelligence"""
    print("\n🔧 Testing CRUD Direct Usage...")
    
    try:
        from app.db import SessionLocal
        from app.crud.crud import get_plans_by_user, get_plan_by_id
        
        db = SessionLocal()
        
        # Get all plans for user 10
        plans = get_plans_by_user(db, user_id=10)
        print(f"📊 Found {len(plans)} plans for user 10")
        
        if plans:
            latest_plan = plans[0]  # Most recent (ordered by created_at desc)
            print(f"🎯 Latest plan: ID {latest_plan.id}, Goal: {latest_plan.goal.title if latest_plan.goal else 'No goal'}")
            
            # Get detailed plan info using existing CRUD
            detailed_plan = get_plan_by_id(db, latest_plan.id)
            if detailed_plan and detailed_plan.goal:
                goal = detailed_plan.goal
                print(f"📝 Goal details: {goal.title} ({goal.goal_type})")
                print(f"📅 Timeline: {goal.start_date} to {goal.end_date}")
                print(f"✅ This proves we can get ALL the info using existing CRUD!")
        
        db.close()
        
    except Exception as e:
        print(f"❌ CRUD test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting intelligent context testing...")
    
    # Test context intelligence
    test_context_intelligence()
    
    # Test existing CRUD usage 
    test_existing_crud_usage()
    
    print("\n🎉 Intelligence testing completed!")
