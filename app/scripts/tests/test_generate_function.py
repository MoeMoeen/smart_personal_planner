#!/usr/bin/env python3
# Test the generate_plan_from_ai function directly

import sys
import os
sys.path.append('/home/moemoeen/Documents/GitHub/Python_Projects_Personal/smart_personal_planner')

from app.routers.planning import generate_plan_from_ai
from app.ai.schemas import GoalDescriptionRequest
from app.db import SessionLocal

def test_generate_plan_from_ai():
    print("🧪 Testing generate_plan_from_ai function directly...")
    
    try:
        # Create a database session
        db = SessionLocal()
        
        # Create the request object
        request = GoalDescriptionRequest(
            goal_description="I want to read 12 books this year",
            user_id=1  # Use existing user ID
        )
        
        print(f"📝 Request: {request}")
        print("⚡ Calling generate_plan_from_ai...")
        
        result = generate_plan_from_ai(request=request, db=db)
        
        print(f"✅ Result type: {type(result)}")
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    test_generate_plan_from_ai()
