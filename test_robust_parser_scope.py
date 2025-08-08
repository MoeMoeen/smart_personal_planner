#!/usr/bin/env python3
"""
Test to prove that the problematic response passes schema validation
but fails logical completeness validation
"""

import sys
sys.path.append('/home/moemoeen/Documents/GitHub/Python_Projects_Personal/smart_personal_planner')

from app.ai.schemas import GeneratedPlan

def test_schema_vs_logic_validation():
    """Demonstrate that schema validation != logical completeness"""
    
    # The problematic response that you showed
    problematic_data = {
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
    
    # Test 1: Schema Validation (what RobustParser checks)
    try:
        plan = GeneratedPlan.model_validate(problematic_data)
        print("✅ SCHEMA VALIDATION: PASSED")
        print(f"   - goal_recurrence_count: {plan.plan.goal_recurrence_count}")
        print(f"   - All required fields present")
    except Exception as e:
        print(f"❌ SCHEMA VALIDATION: FAILED - {e}")
        return
    
    # Test 2: Logical Completeness (what we need to check)
    expected_occurrences = plan.plan.goal_recurrence_count
    actual_occurrences = sum(len(cycle.occurrences) for cycle in plan.plan.habit_cycles or [])
    completeness_ratio = actual_occurrences / expected_occurrences
    
    print(f"\n📊 LOGICAL COMPLETENESS ANALYSIS:")
    print(f"   - Expected occurrences: {expected_occurrences}")
    print(f"   - Actual occurrences: {actual_occurrences}")
    print(f"   - Completeness: {completeness_ratio:.1%}")
    
    if completeness_ratio < 0.9:
        print("❌ LOGICAL COMPLETENESS: FAILED")
        print("   - Data is incomplete despite valid schema")
    else:
        print("✅ LOGICAL COMPLETENESS: PASSED")
    
    # Test 3: Timeline Consistency
    timeline_days = (plan.plan.end_date - plan.plan.start_date).days + 1
    print(f"\n📅 TIMELINE ANALYSIS:")
    print(f"   - Timeline days: {timeline_days}")
    print(f"   - Expected daily occurrences: {timeline_days}")
    print(f"   - Actual occurrences: {actual_occurrences}")
    
    if abs(timeline_days - expected_occurrences) > 10:
        print("❌ TIMELINE CONSISTENCY: FAILED")
    else:
        print("✅ TIMELINE CONSISTENCY: PASSED")
    
    print(f"\n🎯 CONCLUSION:")
    print(f"   - Schema validation: WORKS (RobustParser does its job)")
    print(f"   - Logical validation: NEEDED (What's missing)")
    print(f"   - RobustParser is NOT responsible for data completeness")

if __name__ == "__main__":
    test_schema_vs_logic_validation()
