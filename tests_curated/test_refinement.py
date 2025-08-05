#!/usr/bin/env python3
"""
Quick Test of Plan Refinement Fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_refinement_fix():
    """Test the plan refinement with new user_id to avoid conflicts"""
    
    print("🧪 TESTING PLAN REFINEMENT FIX")
    print("=" * 40)
    
    try:
        from app.agent.tools import _plan_feedback_helper
        
        # Test with a simple refinement scenario
        # First we need a plan to refine - use the one from our previous test
        plan_id = 84  # From our previous test
        
        print(f"📝 Testing refinement for plan ID: {plan_id}")
        
        result = _plan_feedback_helper(
            plan_id=plan_id,
            feedback_text="Change frequency to 1 book per month instead of 2",
            action="refine",
            user_id=777,  # Different user to avoid conflicts
            suggested_changes="Reduce from 2 books to 1 book per month"
        )
        
        print("🔄 Refinement Result:")
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        
        if result.get('status') == 'success':
            print("✅ Refinement successful!")
            if result.get('refined_plan_id'):
                print(f"📋 New plan ID: {result.get('refined_plan_id')}")
        else:
            print(f"❌ Refinement failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refinement_fix()
