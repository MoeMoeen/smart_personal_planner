#!/usr/bin/env python3
"""
Test script for plan_feedback endpoint error handling
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8001"

def test_invalid_plan_id():
    """Test with invalid plan ID"""
    print("=== Testing with INVALID plan ID ===")
    
    payload = {
        "plan_id": 99999,  # Non-existent plan ID
        "goal_id": 5,
        "feedback_text": "This should fail",
        "plan_feedback_action": "approve",
        "suggested_changes": None,
        "user_id": 2
    }
    
    try:
        response = requests.post(f"{BASE_URL}/planning/plan-feedback", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 404:
            print("✅ Invalid plan ID test passed (correctly returned 404)!")
        else:
            print("❌ Invalid plan ID test failed!")
            
    except Exception as e:
        print(f"❌ Error testing invalid plan ID: {e}")
    
    print("\n" + "="*50 + "\n")

def test_duplicate_feedback():
    """Test submitting feedback for a plan that already has feedback"""
    print("=== Testing DUPLICATE feedback ===")
    
    # Plan 5 should now have feedback from our previous test
    payload = {
        "plan_id": 5,
        "goal_id": 6,
        "feedback_text": "This should fail because feedback already exists",
        "plan_feedback_action": "approve",
        "suggested_changes": None,
        "user_id": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/planning/plan-feedback", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Duplicate feedback test passed (correctly returned 400)!")
        else:
            print("❌ Duplicate feedback test failed!")
            
    except Exception as e:
        print(f"❌ Error testing duplicate feedback: {e}")
    
    print("\n" + "="*50 + "\n")

def test_missing_action():
    """Test with missing feedback action"""
    print("=== Testing with MISSING feedback action ===")
    
    payload = {
        "plan_id": 7,
        "goal_id": 7,
        "feedback_text": "This should fail",
        "suggested_changes": None,
        "user_id": 9
        # Missing plan_feedback_action
    }
    
    try:
        response = requests.post(f"{BASE_URL}/planning/plan-feedback", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 422:  # Validation error
            print("✅ Missing action test passed (correctly returned validation error)!")
        else:
            print("❌ Missing action test failed!")
            
    except Exception as e:
        print(f"❌ Error testing missing action: {e}")
    
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
    print("🚀 Starting plan_feedback error handling tests\n")
    
    # Check if API is running
    if not check_api_health():
        print("Please make sure the FastAPI server is running on http://localhost:8001")
        exit(1)
    
    print("\n" + "="*50 + "\n")
    
    # Run all tests
    test_invalid_plan_id()
    test_duplicate_feedback()
    test_missing_action()
    
    print("🏁 All error handling tests completed!")
