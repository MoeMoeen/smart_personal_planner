# app/cognitive/world/validator.py
""" 
Validator for world state and task scheduling 
This module provides validation logic for tasks against the world state,
ensuring they adhere to constraints and do not conflict with existing tasks.
"""

from typing import List, Dict, Optional
from datetime import datetime, time, timedelta
import uuid

from pydantic import BaseModel, Field
from .world_state import CalendarizedTask, WorldState, WorldStateValidation


class ValidationResult(BaseModel):
    """Result of task validation"""
    is_valid: bool
    conflicts: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class OverlapDetails(BaseModel):
    """Details about task overlap"""
    task1: CalendarizedTask
    task2: CalendarizedTask
    overlap_start: datetime
    overlap_end: datetime
    overlap_duration: timedelta
    
    @property
    def overlap_minutes(self) -> int:
        return int(self.overlap_duration.total_seconds() / 60)


class WorldValidator:
    """Validates tasks against world state and constraints"""
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state
    
    def validate_task(self, task: CalendarizedTask) -> ValidationResult:
        """
        Comprehensive validation of a single task against world state
        
        Args:
            task: Task to validate
            
        Returns:
            ValidationResult with conflicts, warnings, and suggestions
        """
        result = ValidationResult(is_valid=True)
        
        # Validate different aspects of the task
        self._validate_conflicts(task, result)
        self._validate_capacity(task, result)
        self._validate_availability(task, result)
        self._suggest_resolutions(task, result)
        
        return result
    
    def _validate_conflicts(self, task: CalendarizedTask, result: ValidationResult) -> None:
        """Check for time conflicts with existing tasks"""
        conflicts = self._check_time_conflicts(task)
        if conflicts:
            result.is_valid = False
            result.conflicts.extend([f"Time conflict with task: {c.task2.title}" for c in conflicts])
    
    def _validate_capacity(self, task: CalendarizedTask, result: ValidationResult) -> None:
        """Check capacity constraints"""
        capacity_issues = self._check_capacity_constraints(task)
        if capacity_issues:
            result.warnings.extend(capacity_issues)
    
    def _validate_availability(self, task: CalendarizedTask, result: ValidationResult) -> None:
        """Check availability window constraints"""
        availability_issues = self._check_availability_constraints(task)
        if availability_issues:
            result.is_valid = False
            result.conflicts.extend(availability_issues)
    
    def _suggest_resolutions(self, task: CalendarizedTask, result: ValidationResult) -> None:
        """Generate optimization suggestions"""
        conflicts = self._check_time_conflicts(task)
        suggestions = self._generate_suggestions(task, conflicts)
        result.suggestions.extend(suggestions)
    
    def validate_task_list(self, tasks: List[CalendarizedTask]) -> Dict[str, ValidationResult]:
        """
        Validate a list of tasks for internal conflicts and world state conflicts
        
        Args:
            tasks: List of tasks to validate
            
        Returns:
            Dictionary mapping task IDs to their validation results
        """
        results = {}
        
        # First, check each task against current world state
        for task in tasks:
            results[task.task_id] = self.validate_task(task)
        
        # Then, check for internal conflicts between the new tasks
        internal_conflicts = self._check_internal_conflicts(tasks)
        for task_id, conflicts in internal_conflicts.items():
            if task_id in results:
                results[task_id].conflicts.extend(conflicts)
                if conflicts:
                    results[task_id].is_valid = False
        
        return results
    
    def _check_time_conflicts(self, task: CalendarizedTask) -> List[OverlapDetails]:
        """Check for time overlaps with existing tasks"""
        conflicts = []
        
        for existing_task in self.world_state.all_tasks:
            if existing_task.task_id == task.task_id:
                continue
                
            overlap = self._calculate_overlap(task, existing_task)
            if overlap:
                conflicts.append(overlap)
        
        return conflicts
    
    def _calculate_overlap(self, task1: CalendarizedTask, task2: CalendarizedTask) -> Optional[OverlapDetails]:
        """Calculate overlap between two tasks if it exists"""
        # Get datetime objects directly
        start1 = task1.start_datetime
        end1 = task1.end_datetime
        start2 = task2.start_datetime
        end2 = task2.end_datetime
        
        # Find overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start < overlap_end:
            return OverlapDetails(
                task1=task1,
                task2=task2,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                overlap_duration=overlap_end - overlap_start
            )
        
        return None
    
    def _check_capacity_constraints(self, task: CalendarizedTask) -> List[str]:
        """Check if task exceeds daily/weekly capacity limits"""
        warnings = []
        
        if not self.world_state.capacity:
            return warnings
        
        # Get task date from start_datetime
        task_date = task.start_datetime.date()
        
        # Check daily capacity using current_daily_load
        date_str = task_date.isoformat()
        current_load = self.world_state.capacity.current_daily_load.get(date_str, 0.0)
        task_hours = task.estimated_minutes / 60.0
        daily_limit = self.world_state.capacity.constraints.max_hours_per_day
        
        if current_load + task_hours > daily_limit:
            warnings.append(
                f"Adding this task ({task_hours:.1f}h) would exceed daily limit "
                f"({current_load + task_hours:.1f}h > {daily_limit}h)"
            )
        
        # Check weekly capacity
        week_start = task_date - timedelta(days=task_date.weekday())
        week_key = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"
        current_weekly_load = self.world_state.capacity.current_weekly_load.get(week_key, 0.0)
        weekly_limit = self.world_state.capacity.constraints.max_hours_per_week
        
        if current_weekly_load + task_hours > weekly_limit:
            warnings.append(
                f"Adding this task would exceed weekly limit "
                f"({current_weekly_load + task_hours:.1f}h > {weekly_limit}h)"
            )
        
        return warnings
    
    def _check_availability_constraints(self, task: CalendarizedTask) -> List[str]:
        """Check if task falls within available time windows"""
        conflicts = []
        
        if not self.world_state.availability:
            return conflicts
        
        # Get task date and times
        task_date = task.start_datetime.date()
        task_start_time = task.start_datetime.time()
        task_end_time = task.end_datetime.time()
        
        # Check default weekly pattern
        weekday = task_date.strftime('%A').lower()
        if weekday in self.world_state.availability.default_weekly_pattern:
            available_ranges = self.world_state.availability.default_weekly_pattern[weekday]
            
            if not self._task_fits_in_time_ranges(task_start_time, task_end_time, available_ranges):
                time_ranges_str = ", ".join([f"{tr.start_time}-{tr.end_time}" for tr in available_ranges])
                conflicts.append(
                    f"Task time ({task_start_time}-{task_end_time}) falls outside "
                    f"available windows for {weekday.title()}: {time_ranges_str}"
                )
        
        # Check date-specific availability
        for day_availability in self.world_state.availability.date_specific:
            if day_availability.date == task_date:
                if day_availability.is_blackout:
                    conflicts.append(f"Task scheduled on blackout date: {task_date}")
                elif not self._task_fits_in_time_ranges(task_start_time, task_end_time, day_availability.available_ranges):
                    time_ranges_str = ", ".join([f"{tr.start_time}-{tr.end_time}" for tr in day_availability.available_ranges])
                    conflicts.append(f"Task time falls outside available windows for {task_date}: {time_ranges_str}")
                break
        
        return conflicts
    
    def _task_fits_in_time_ranges(self, task_start_time: time, task_end_time: time, time_ranges: List) -> bool:
        """Check if task fits within any of the available time ranges"""
        for time_range in time_ranges:
            window_start = time_range.start_time
            window_end = time_range.end_time
            
            # Handle windows that span midnight
            if window_end < window_start:
                # Split into two windows: start to midnight, midnight to end
                if (task_start_time >= window_start or task_end_time <= window_end) and \
                   (task_end_time <= window_end or task_start_time >= window_start):
                    return True
            else:
                # Normal window
                if task_start_time >= window_start and task_end_time <= window_end:
                    return True
        
        return False
    
    def _check_internal_conflicts(self, tasks: List[CalendarizedTask]) -> Dict[str, List[str]]:
        """Check for conflicts between tasks in the provided list"""
        conflicts = {task.task_id: [] for task in tasks}
        
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks[i+1:], i+1):
                overlap = self._calculate_overlap(task1, task2)
                if overlap:
                    conflicts[task1.task_id].append(f"Internal conflict with task: {task2.title}")
                    conflicts[task2.task_id].append(f"Internal conflict with task: {task1.title}")
        
        return conflicts
    
    def _calculate_daily_load(self, date) -> int:
        """Calculate total minutes scheduled for a specific date"""
        total_minutes = 0
        for task in self.world_state.all_tasks:
            task_date = task.start_datetime.date()
            if task_date == date:
                total_minutes += task.estimated_minutes
        return total_minutes
    
    def _calculate_weekly_load(self, week_start) -> int:
        """Calculate total minutes scheduled for a week starting from week_start"""
        total_minutes = 0
        week_end = week_start + timedelta(days=7)
        
        for task in self.world_state.all_tasks:
            task_date = task.start_datetime.date()
            if week_start <= task_date < week_end:
                total_minutes += task.estimated_minutes
        
        return total_minutes
    
    def _calculate_task_duration(self, task: CalendarizedTask) -> int:
        """Calculate task duration in minutes"""
        # Use the estimated_minutes directly as it's more reliable
        return task.estimated_minutes
    
    def _generate_suggestions(self, task: CalendarizedTask, conflicts: List[OverlapDetails]) -> List[str]:
        """Generate suggestions for resolving conflicts"""
        suggestions = []
        
        if conflicts:
            # Suggest alternative time slots
            suggestions.append("Consider rescheduling to avoid conflicts")
            
            # Find next available slot
            next_slot = self._find_next_available_slot(task)
            if next_slot:
                suggestions.append(f"Next available slot: {next_slot}")
        
        # Suggest capacity optimization
        task_date = task.start_datetime.date()
        if self._is_day_overloaded(task_date):
            suggestions.append("Consider moving some tasks to less busy days")
        
        return suggestions
    
    def _find_next_available_slot(self, task: CalendarizedTask) -> Optional[str]:
        """Find the next available time slot for the task"""
        # This is a simplified implementation
        # In a real system, this would be more sophisticated
        current_date = task.start_datetime.date()
        task_duration = task.estimated_minutes
        
        # Check next 7 days
        for days_ahead in range(1, 8):
            check_date = current_date + timedelta(days=days_ahead)
            available_slot = self._find_slot_on_date(check_date, task_duration)
            if available_slot:
                return f"{check_date.isoformat()} at {available_slot}"
        
        return None
    
    def _find_slot_on_date(self, date, duration_minutes: int) -> Optional[str]:
        """Find an available slot on a specific date"""
        # Simplified: just return morning slot if no conflicts
        morning_start = datetime.combine(date, time(9, 0))
        morning_end = morning_start + timedelta(minutes=duration_minutes)
        
        # Check if this slot conflicts with existing tasks
        test_task = CalendarizedTask(
            task_id=str(uuid.uuid4()),
            title="temp_slot_check",
            goal_id="temp",
            plan_id="temp",
            start_datetime=morning_start,
            end_datetime=morning_end,
            estimated_minutes=duration_minutes,
            priority=1
        )
        
        conflicts = self._check_time_conflicts(test_task)
        if not conflicts:
            return f"{morning_start.time()}-{morning_end.time()}"
        
        return None
    
    def _is_day_overloaded(self, date) -> bool:
        """Check if a day is overloaded with tasks"""
        if not self.world_state.capacity:
            return False
        
        date_str = date.isoformat()
        current_load = self.world_state.capacity.current_daily_load.get(date_str, 0.0)
        daily_limit = self.world_state.capacity.constraints.max_hours_per_day
        return current_load > daily_limit * 0.8  # 80% threshold


def validate_world_consistency(world_state: WorldState) -> ValidationResult:
    """
    Validate the overall consistency of the world state
    
    Args:
        world_state: World state to validate
        
    Returns:
        ValidationResult for the entire world state
    """
    validator = WorldValidator(world_state)
    result = ValidationResult(is_valid=True)
    
    # Check all existing tasks for conflicts
    for task in world_state.all_tasks:
        task_result = validator.validate_task(task)
        if not task_result.is_valid:
            result.is_valid = False
            result.conflicts.extend([f"Task {task.title}: {c}" for c in task_result.conflicts])
        
        result.warnings.extend([f"Task {task.title}: {w}" for w in task_result.warnings])
    
    return result


def build_world_state_validation(task_results: Dict[str, ValidationResult], user_id: str) -> WorldStateValidation:
    """
    Convert per-task validation results into a world-level summary
    
    Args:
        task_results: Dictionary mapping task IDs to their validation results
        user_id: User ID for the validation
        
    Returns:
        WorldStateValidation with summary information
    """
    # Aggregate conflicts and violations
    all_conflicts = []
    capacity_violations = []
    availability_violations = []
    
    for task_id, result in task_results.items():
        for conflict in result.conflicts:
            if "capacity" in conflict.lower() or "limit" in conflict.lower():
                capacity_violations.append(f"Task {task_id}: {conflict}")
            elif "availability" in conflict.lower() or "window" in conflict.lower():
                availability_violations.append(f"Task {task_id}: {conflict}")
            else:
                # Convert to TaskConflict (simplified - would need proper conflict parsing)
                pass
        
        # Add capacity warnings as violations
        for warning in result.warnings:
            if "capacity" in warning.lower() or "limit" in warning.lower():
                capacity_violations.append(f"Task {task_id}: {warning}")
    
    total_issues = len(all_conflicts) + len(capacity_violations) + len(availability_violations)
    is_valid = total_issues == 0
    
    return WorldStateValidation(
        user_id=user_id,
        is_valid=is_valid,
        conflicts=all_conflicts,
        capacity_violations=capacity_violations,
        availability_violations=availability_violations,
        total_issues=total_issues
    )
