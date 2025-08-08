#!/usr/bin/env python3
"""
Test the problematic response structure to identify all issues
"""

import sys
import json
from datetime import datetime, date
from typing import Dict, Any
sys.path.append('/home/moemoeen/Documents/GitHub/Python_Projects_Personal/smart_personal_planner')

from app.ai.schemas import GeneratedPlan, GoalPlan, PlanStructure
from app.models import GoalType

def test_problematic_response():
    """Test the actual response structure and identify all issues"""
    
    # The problematic response from the user
    response_data = {
        "goal": {
            "title": "Learn FastAPI Development",
            "description": "Master FastAPI framework for building modern web APIs",
            "user_id": 1
        },
        "plan": {
            "goal_type": "hybrid",
            "start_date": "2025-08-09",
            "end_date": "2026-02-09",
            "progress": 0,
            "recurrence_cycle": "daily",
            "goal_frequency_per_cycle": 1,
            "goal_recurrence_count": 185,
            "default_estimated_time_per_cycle": 120,
            "habit_cycles": [
                {
                    "cycle_label": "2025-08",
                    "start_date": "2025-08-09",
                    "end_date": "2025-08-31",
                    "progress": 0,
                    "occurrences": [
                        {
                            "occurrence_order": 1,
                            "estimated_effort": 120,
                            "tasks": [
                                {
                                    "title": "Study FastAPI basics",
                                    "due_date": "2025-08-09",
                                    "estimated_time": 60,
                                    "completed": False
                                },
                                {
                                    "title": "Practice FastAPI basics",
                                    "due_date": "2025-08-09",
                                    "estimated_time": 60,
                                    "completed": False
                                }
                            ]
                        },
                        {
                            "occurrence_order": 2,
                            "estimated_effort": 120,
                            "tasks": [
                                {
                                    "title": "Study FastAPI routing",
                                    "due_date": "2025-08-10",
                                    "estimated_time": 60,
                                    "completed": False
                                },
                                {
                                    "title": "Practice FastAPI routing",
                                    "due_date": "2025-08-10",
                                    "estimated_time": 60,
                                    "completed": False
                                }
                            ]
                        }
                    ]
                }
            ],
            "tasks": [
                {
                    "title": "Complete FastAPI tutorial",
                    "due_date": "2025-09-09",
                    "estimated_time": 600,
                    "completed": False
                },
                {
                    "title": "Build a simple API with FastAPI",
                    "due_date": "2025-10-10",
                    "estimated_time": 1200,
                    "completed": False
                },
                {
                    "title": "Build a complex API with FastAPI",
                    "due_date": "2025-12-12",
                    "estimated_time": 2400,
                    "completed": False
                },
                {
                    "title": "Deploy FastAPI application",
                    "due_date": "2026-02-09",
                    "estimated_time": 600,
                    "completed": False
                }
            ]
        },
        "ai_model_used": "GPT-3",
        "ai_prompt_version": "1.0",
        "generated_at": "2025-08-08T00:00:00Z",
        "refinement_round": 0,
        "source_plan_id": None,
        "user_id": 1
    }
    
    print("=== TESTING PROBLEMATIC RESPONSE ===")
    
    issues = []
    
    # Test 1: Schema Parsing
    try:
        plan = GeneratedPlan.model_validate(response_data)
        print("✅ Schema parsing: PASSED")
    except Exception as e:
        issues.append(f"❌ Schema parsing: {e}")
        print(f"❌ Schema parsing: {e}")
        return issues
    
    # Test 2: Data Completeness Analysis
    plan_data = plan.plan
    expected_days = 185  # goal_recurrence_count
    actual_occurrences = sum(len(cycle.occurrences) for cycle in plan_data.habit_cycles or [])
    
    completeness_ratio = actual_occurrences / expected_days
    print(f"📊 Data Completeness: {actual_occurrences}/{expected_days} = {completeness_ratio:.1%}")
    
    if completeness_ratio < 0.95:  # Less than 95% complete
        issues.append(f"❌ Data Completeness: Only {completeness_ratio:.1%} of required data provided")
    
    # Test 3: Timeline Consistency
    start_date = plan_data.start_date
    end_date = plan_data.end_date
    if end_date:
        total_days = (end_date - start_date).days + 1
        expected_occurrences = total_days if plan_data.recurrence_cycle == "daily" else None
        
        if expected_occurrences and abs(expected_occurrences - expected_days) > 5:
            issues.append(f"❌ Timeline Inconsistency: {total_days} days timeline vs {expected_days} expected occurrences")
    
    # Test 4: Cycle Coverage Analysis
    if plan_data.habit_cycles:
        first_cycle = plan_data.habit_cycles[0]
        cycle_days = (first_cycle.end_date - first_cycle.start_date).days + 1
        cycle_occurrences = len(first_cycle.occurrences)
        
        if cycle_days != cycle_occurrences:
            issues.append(f"❌ Cycle Coverage: {cycle_days} days in cycle vs {cycle_occurrences} occurrences")
    
    # Test 5: Missing Cycles Analysis
    if plan_data.habit_cycles and len(plan_data.habit_cycles) == 1:
        issues.append(f"❌ Missing Cycles: Only 1 cycle provided for 6-month plan")
    
    # Test 6: Time Estimation Realism
    daily_time = plan_data.default_estimated_time_per_cycle or 0
    if daily_time > 180:  # More than 3 hours daily
        issues.append(f"⚠️  Unrealistic Time: {daily_time} minutes daily might be excessive")
    
    # Test 7: Task Time Distribution
    if plan_data.tasks:
        max_task_time = max(task.estimated_time for task in plan_data.tasks)
        if max_task_time > 1800:  # More than 30 hours
            issues.append(f"⚠️  Excessive Task Time: {max_task_time} minutes for single task")
    
    print(f"\n🔍 ANALYSIS COMPLETE: {len(issues)} issues found")
    for issue in issues:
        print(issue)
    
    return issues

if __name__ == "__main__":
    issues = test_problematic_response()
    print(f"\n📋 TOTAL ISSUES: {len(issues)}")
    if len(issues) > 0:
        print("🚨 VERDICT: COMPLETELY UNUSABLE - REQUIRES TOTAL RECONSTRUCTION")
    else:
        print("✅ VERDICT: ACCEPTABLE")
