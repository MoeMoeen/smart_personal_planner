#!/usr/bin/env python3
"""
Test script for the plan_feedback endpoint - REQUEST_REFINEMENT
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8001"

def test_plan_feedback_refinement():
    """Test requesting plan refinement"""
    print("=== Testing REQUEST_REFINEMENT plan feedback ===")
    
    # Use plan ID 12 from our database (should not have feedback yet)
    payload = {
        "plan_id": 12,
        "goal_id": 8,
        "feedback_text": "This plan needs more detailed tasks and better time allocation.",
        "plan_feedback_action": "request_refinement",
        "suggested_changes": "Add more specific milestones and break down large tasks into smaller ones",
        "user_id": 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/planning/plan-feedback", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ REQUEST_REFINEMENT test passed!")
        else:
            print("❌ REQUEST_REFINEMENT test failed!")
            
    except Exception as e:
        print(f"❌ Error testing REQUEST_REFINEMENT: {e}")
    
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
    print("🚀 Starting REQUEST_REFINEMENT test\n")
    
    # Check if API is running
    if not check_api_health():
        print("Please make sure the FastAPI server is running on http://localhost:8001")
        exit(1)
    
    print("\n" + "="*50 + "\n")
    
    # Run the test
    test_plan_feedback_refinement()
    
    print("🏁 Test completed!")
