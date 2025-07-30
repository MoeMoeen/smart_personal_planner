#!/usr/bin/env python3
"""
Simple test script for the plan_feedback endpoint - APPROVE only
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8001"

def test_plan_feedback_approve_simple():
    """Test approving a plan that doesn't have feedback yet"""
    print("=== Testing APPROVE plan feedback (Simple) ===")
    
    # Use plan ID 5 from our database (should not have feedback yet)
    payload = {
        "plan_id": 5,
        "goal_id": 6,
        "feedback_text": "This plan looks great! I approve it.",
        "plan_feedback_action": "approve",
        "suggested_changes": None,
        "user_id": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/planning/plan-feedback", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ APPROVE test passed!")
        else:
            print("❌ APPROVE test failed!")
            
    except Exception as e:
        print(f"❌ Error testing APPROVE: {e}")
    
    print("\n" + "="*50 + "\n")

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ API is running!")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting simple plan_feedback endpoint test\n")
    
    # Check if API is running
    if not check_api_health():
        print("Please make sure the FastAPI server is running on http://localhost:8001")
        exit(1)
    
    print("\n" + "="*50 + "\n")
    
    # Run the test
    test_plan_feedback_approve_simple()
    
    print("🏁 Test completed!")
