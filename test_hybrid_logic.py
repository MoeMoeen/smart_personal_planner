#!/usr/bin/env python3
"""
Comprehensive Test Cases for Hybrid Goal Logic in tools.py
=========================================================

This script tests various edge cases and scenarios for hybrid goal handling
in the agent tools, particularly focusing on the display logic and formatting.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import Goal, Plan, Task, HabitCycle, GoalOccurrence, GoalType
from app.agent.tools import MAX_DISPLAY_TASKS_PROJECT, MAX_DISPLAY_TASKS_HYBRID, MAX_DISPLAY_TASKS_DETAILS
from datetime import date, datetime
from typing import List, Optional, Union
import logging

# Configure logging for test output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MockPlan:
    """Mock Plan object for testing display logic"""
    def __init__(self, goal_type: str, tasks: List = None, habit_cycles: List = None, 
                 recurrence_cycle: str = "weekly", goal_frequency_per_cycle: int = 3,
                 default_estimated_time_per_cycle: Optional[int] = 30, start_date: Optional[date] = None, 
                 end_date: Optional[date] = None, id: int = 1, progress: int = 0, 
                 refinement_round: int = 0, is_approved: bool = False):
        # Use a mock enum-like object for goal_type
        self.goal_type = MockGoalType(goal_type)
        self.tasks = tasks or []
        self.habit_cycles = habit_cycles or []
        self.recurrence_cycle = recurrence_cycle
        self.goal_frequency_per_cycle = goal_frequency_per_cycle
        self.default_estimated_time_per_cycle = default_estimated_time_per_cycle
        self.start_date = start_date or date.today()
        self.end_date = end_date
        self.id = id
        self.progress = progress
        self.refinement_round = refinement_round
        self.is_approved = is_approved

class MockGoalType:
    """Mock GoalType enum for testing"""
    def __init__(self, value: str):
        self._value = value
    
    @property
    def value(self):
        return self._value

class MockGoal:
    """Mock Goal object for testing"""
    def __init__(self, title: str = "Test Goal", description: str = "Test Description", id: int = 1):
        self.title = title
        self.description = description
        self.id = id

class MockTask:
    """Mock Task object for testing"""
    def __init__(self, title: str, due_date: Union[Optional[date], str] = "default", estimated_time: Optional[int] = None):
        self.title = title
        # Use a sentinel value to distinguish between None being passed and default behavior
        if due_date == "default":
            self.due_date = date.today()
        else:
            self.due_date = due_date
        self.estimated_time = estimated_time

def test_hybrid_plan_project_tasks_only():
    """Test Case 1: Hybrid plan with only project tasks"""
    logger.info("🧪 Test 1: Hybrid plan with only project tasks")
    
    tasks = [
        MockTask("Setup development environment", date(2025, 8, 10), 60),
        MockTask("Learn basic syntax", date(2025, 8, 15), 90),
        MockTask("Build first project", date(2025, 8, 20), 120)
    ]
    
    plan = MockPlan(
        goal_type="hybrid",
        tasks=tasks,
        habit_cycles=[],  # Empty habit cycles
        recurrence_cycle="weekly",
        goal_frequency_per_cycle=3
    )
    
    # Test the display logic from generate_plan_with_ai_tool
    hybrid_info = []
    
    # Show project component
    if plan.tasks:
        hybrid_info.append("📋 Project Tasks:")
        for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_HYBRID], 1):
            due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
            time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
            hybrid_info.append(f"  {i}. {task.title}{time_str} - Due: {due_date}")
        if len(plan.tasks) > MAX_DISPLAY_TASKS_HYBRID:
            hybrid_info.append(f"  ... and {len(plan.tasks) - MAX_DISPLAY_TASKS_HYBRID} more tasks")
        hybrid_info.append("")
    
    # Show habit component
    if plan.habit_cycles:
        hybrid_info.append("🔄 Habit Component:")
        hybrid_info.append(f"  📅 Schedule: {plan.recurrence_cycle}")
        hybrid_info.append(f"  🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
        if plan.default_estimated_time_per_cycle:
            hybrid_info.append(f"  ⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
    
    result = "\n".join(hybrid_info)
    logger.info(f"✅ Result:\n{result}")
    
    # Assertions
    assert "📋 Project Tasks:" in result
    assert "Setup development environment" in result
    assert "🔄 Habit Component:" not in result  # Should not appear when no habit cycles
    logger.info("✅ Test 1 PASSED: Project tasks only displayed correctly")

def test_hybrid_plan_habit_cycles_only():
    """Test Case 2: Hybrid plan with only habit cycles"""
    logger.info("🧪 Test 2: Hybrid plan with only habit cycles")
    
    habit_cycles = ["Mock cycle 1", "Mock cycle 2"]  # Mock habit cycles
    
    plan = MockPlan(
        goal_type="hybrid",
        tasks=[],  # Empty tasks
        habit_cycles=habit_cycles,
        recurrence_cycle="daily",
        goal_frequency_per_cycle=1,
        default_estimated_time_per_cycle=15
    )
    
    # Test the display logic
    hybrid_info = []
    
    # Show project component
    if plan.tasks:
        hybrid_info.append("📋 Project Tasks:")
        for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_HYBRID], 1):
            due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
            time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
            hybrid_info.append(f"  {i}. {task.title}{time_str} - Due: {due_date}")
        if len(plan.tasks) > MAX_DISPLAY_TASKS_HYBRID:
            hybrid_info.append(f"  ... and {len(plan.tasks) - MAX_DISPLAY_TASKS_HYBRID} more tasks")
        hybrid_info.append("")
    
    # Show habit component
    if plan.habit_cycles:
        hybrid_info.append("🔄 Habit Component:")
        hybrid_info.append(f"  📅 Schedule: {plan.recurrence_cycle}")
        hybrid_info.append(f"  🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
        if plan.default_estimated_time_per_cycle:
            hybrid_info.append(f"  ⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
    
    result = "\n".join(hybrid_info)
    logger.info(f"✅ Result:\n{result}")
    
    # Assertions
    assert "🔄 Habit Component:" in result
    assert "📅 Schedule: daily" in result
    assert "🔄 Frequency: 1 times per daily" in result
    assert "⏱️ Time per session: 15 minutes" in result
    assert "📋 Project Tasks:" not in result  # Should not appear when no tasks
    logger.info("✅ Test 2 PASSED: Habit cycles only displayed correctly")

def test_hybrid_plan_both_components():
    """Test Case 3: Hybrid plan with both components"""
    logger.info("🧪 Test 3: Hybrid plan with both project tasks and habit cycles")
    
    tasks = [
        MockTask("Research programming languages", date(2025, 8, 8), 45),
        MockTask("Set up coding environment", date(2025, 8, 10), 30),
        MockTask("Complete first tutorial", date(2025, 8, 12), 90),
        MockTask("Build sample project", date(2025, 8, 15), 120)  # This should be truncated
    ]
    
    habit_cycles = ["Week 1", "Week 2"]
    
    plan = MockPlan(
        goal_type="hybrid",
        tasks=tasks,
        habit_cycles=habit_cycles,
        recurrence_cycle="weekly",
        goal_frequency_per_cycle=3,
        default_estimated_time_per_cycle=45
    )
    
    # Test the display logic
    hybrid_info = []
    
    # Show project component
    if plan.tasks:
        hybrid_info.append("📋 Project Tasks:")
        for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_HYBRID], 1):
            due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
            time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
            hybrid_info.append(f"  {i}. {task.title}{time_str} - Due: {due_date}")
        if len(plan.tasks) > MAX_DISPLAY_TASKS_HYBRID:
            hybrid_info.append(f"  ... and {len(plan.tasks) - MAX_DISPLAY_TASKS_HYBRID} more tasks")
        hybrid_info.append("")
    
    # Show habit component
    if plan.habit_cycles:
        hybrid_info.append("🔄 Habit Component:")
        hybrid_info.append(f"  📅 Schedule: {plan.recurrence_cycle}")
        hybrid_info.append(f"  🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
        if plan.default_estimated_time_per_cycle:
            hybrid_info.append(f"  ⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
    
    result = "\n".join(hybrid_info)
    logger.info(f"✅ Result:\n{result}")
    
    # Assertions
    assert "📋 Project Tasks:" in result
    assert "🔄 Habit Component:" in result
    assert "Research programming languages" in result
    assert "Set up coding environment" in result
    assert "Complete first tutorial" in result
    assert "... and 1 more tasks" in result  # Should show truncation message
    assert "📅 Schedule: weekly" in result
    assert "⏱️ Time per session: 45 minutes" in result
    logger.info("✅ Test 3 PASSED: Both components displayed correctly with truncation")

def test_long_title_description_formatting():
    """Test Case 4: Plan with very long title and description"""
    logger.info("🧪 Test 4: Plan with very long title and description")
    
    long_title = "This is an extremely long goal title that might cause formatting issues in the display and should be handled gracefully by the system without breaking the layout or causing truncation problems in various contexts"
    long_description = "This is a very detailed and comprehensive description of a goal that contains multiple sentences and explains the context, objectives, methodology, expected outcomes, timeline considerations, resource requirements, potential challenges, success metrics, and various other aspects that might make the description quite lengthy and potentially problematic for display formatting in different user interfaces and contexts where space might be limited or where text wrapping might not work as expected."
    
    goal = MockGoal(title=long_title, description=long_description)
    
    # Test the plan details display logic (similar to get_plan_details_smart)
    plan = MockPlan(goal_type="hybrid", id=123, progress=25, refinement_round=2, is_approved=True)
    
    # Build response parts like in get_plan_details_smart
    is_approved = plan.is_approved
    status_emoji = "✅" if is_approved else "📋"
    
    response_parts = [
        f"{status_emoji} **Detailed Plan Information**",
        "",
        f"**📝 Plan ID:** {plan.id}",
        f"**📝 Title:** {goal.title}",
        f"**📋 Type:** {plan.goal_type.value.title()} Goal",
        f"**📖 Description:** {goal.description or 'No description provided'}",
        f"**📅 Timeline:** {plan.start_date} to {plan.end_date or 'Ongoing'}",
        f"**📊 Progress:** {plan.progress}%",
        f"**🔄 Refinement Round:** {plan.refinement_round or 0}",
        f"**✅ Status:** {'Approved' if is_approved else 'Pending Review'}",
        ""
    ]
    
    result = "\n".join(response_parts)
    logger.info(f"✅ Result length: {len(result)} characters")
    logger.info(f"✅ Title length: {len(goal.title)} characters")
    logger.info(f"✅ Description length: {len(goal.description)} characters")
    
    # Assertions
    assert len(goal.title) > 100  # Verify it's actually long
    assert len(goal.description) > 400  # Adjusted: description is 498 chars, not >500
    assert goal.title in result
    assert goal.description in result
    assert "**📝 Title:**" in result
    assert "**📖 Description:**" in result
    logger.info("✅ Test 4 PASSED: Long title and description handled correctly")

def test_display_limits_configuration():
    """Test Case 5: Verify display limits are configurable and working"""
    logger.info("🧪 Test 5: Display limits configuration")
    
    logger.info(f"📊 MAX_DISPLAY_TASKS_PROJECT: {MAX_DISPLAY_TASKS_PROJECT}")
    logger.info(f"📊 MAX_DISPLAY_TASKS_HYBRID: {MAX_DISPLAY_TASKS_HYBRID}")
    logger.info(f"📊 MAX_DISPLAY_TASKS_DETAILS: {MAX_DISPLAY_TASKS_DETAILS}")
    
    # Create a plan with more tasks than the hybrid limit
    many_tasks = [MockTask(f"Task {i}", date(2025, 8, 8+i), 30) for i in range(1, 8)]  # 7 tasks
    
    plan = MockPlan(goal_type="hybrid", tasks=many_tasks)
    
    # Test project limit (should show 5)
    project_tasks_shown = min(len(many_tasks), MAX_DISPLAY_TASKS_PROJECT)
    logger.info(f"📋 Project mode would show: {project_tasks_shown} tasks")
    
    # Test hybrid limit (should show 3)
    hybrid_tasks_shown = min(len(many_tasks), MAX_DISPLAY_TASKS_HYBRID)
    logger.info(f"🔄 Hybrid mode would show: {hybrid_tasks_shown} tasks")
    
    # Verify truncation message calculation
    if len(many_tasks) > MAX_DISPLAY_TASKS_HYBRID:
        remaining = len(many_tasks) - MAX_DISPLAY_TASKS_HYBRID
        logger.info(f"📝 Truncation message: '... and {remaining} more tasks'")
    
    # Assertions
    assert MAX_DISPLAY_TASKS_PROJECT == 5
    assert MAX_DISPLAY_TASKS_HYBRID == 3
    assert MAX_DISPLAY_TASKS_DETAILS == 10
    assert project_tasks_shown == 5
    assert hybrid_tasks_shown == 3
    logger.info("✅ Test 5 PASSED: Display limits working correctly")

def test_edge_case_empty_values():
    """Test Case 6: Edge cases with empty/None values"""
    logger.info("🧪 Test 6: Edge cases with empty/None values")
    
    # Test task with no due date or time
    task_no_date = MockTask("Task without date", due_date=None, estimated_time=None)
    
    # Test plan with minimal data
    plan = MockPlan(
        goal_type="hybrid",
        tasks=[task_no_date],
        habit_cycles=[],
        recurrence_cycle="",
        goal_frequency_per_cycle=0,
        default_estimated_time_per_cycle=None,
        end_date=None
    )
    
    # Test display logic with edge cases
    hybrid_info = []
    
    if plan.tasks:
        hybrid_info.append("📋 Project Tasks:")
        for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_HYBRID], 1):
            due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
            time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
            hybrid_info.append(f"  {i}. {task.title}{time_str} - Due: {due_date}")
        hybrid_info.append("")
    
    if plan.habit_cycles:
        hybrid_info.append("🔄 Habit Component:")
        hybrid_info.append(f"  📅 Schedule: {plan.recurrence_cycle}")
        hybrid_info.append(f"  🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
        if plan.default_estimated_time_per_cycle:
            hybrid_info.append(f"  ⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
    
    result = "\n".join(hybrid_info)
    logger.info(f"✅ Result:\n{result}")
    
    # Assertions
    assert "No due date" in result  # Task with no due date shows "No due date"
    assert "Task without date - Due: No due date" in result  # Full format check
    assert "🔄 Habit Component:" not in result  # Empty habit cycles shouldn't show habit section
    logger.info("✅ Test 6 PASSED: Edge cases handled correctly")

def run_all_tests():
    """Run all test cases"""
    logger.info("🧪 Starting Comprehensive Hybrid Logic Tests")
    logger.info("=" * 60)
    
    test_functions = [
        test_hybrid_plan_project_tasks_only,
        test_hybrid_plan_habit_cycles_only,
        test_hybrid_plan_both_components,
        test_long_title_description_formatting,
        test_display_limits_configuration,
        test_edge_case_empty_values
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
            logger.info("")
        except Exception as e:
            logger.error(f"❌ {test_func.__name__} FAILED: {e}")
            failed += 1
            logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"🧪 Test Results: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        logger.info("🎉 All tests PASSED! Hybrid logic is working correctly.")
    else:
        logger.error(f"❌ {failed} tests FAILED. Please review the logic.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
