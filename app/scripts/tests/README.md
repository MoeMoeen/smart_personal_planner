# Test Scripts

This directory contains test scripts created during the development and debugging of the plan feedback endpoint.

## Files Description

### Plan Feedback Testing
- `test_plan_feedback.py` - Comprehensive test suite for the plan feedback endpoint
- `test_simple_feedback.py` - Basic approval feedback tests
- `test_refinement_feedback.py` - Tests for refinement functionality
- `test_error_handling.py` - Error handling and edge case tests

### Test Data Management
- `create_test_plan.py` - Script to create test plans for testing
- `create_test_data.py` - Creates comprehensive test data setup
- `check_plans.py` - Utility to check existing plans in the database

### Test Organization
- `test_setup.py` - Setup script for test environment
- `test_summary.py` - Summary and validation of test results
- `test_feedback_submission.py` - Feedback submission tests

## Usage

These scripts were used to systematically test and debug the plan feedback endpoint, including:
- APPROVE functionality
- REQUEST_REFINEMENT with AI integration
- Error handling for invalid data
- Database validation
- LangChain integration testing

## Notes

- All scripts assume the FastAPI server is running on `http://localhost:8001`
- Scripts use the virtual environment and require proper database setup
- Some scripts create test data that may need cleanup after testing

#=============================================

from app.agent.graph import run_graph_with_message
from pprint import pprint

user_input = """
I'm user 1. I want to build a habit of going to the gym three times a week for the next 3 months. 
Can you create a plan for me?
"""

result = run_graph_with_message(user_input)

for msg in result["messages"]:
    print(f"{msg.type.upper()}:\n{getattr(msg, 'content', None)}\n")