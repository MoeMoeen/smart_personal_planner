# app/cognitive/world/updater.py
"""
World State Updater Module

Maintains world state consistency when tasks change. Handles:
- Dynamic world state maintenance
- Load recalculation and capacity tracking  
- Cache invalidation and query engine coordination
- SQLAlchemy persistence integration
- Future semantic memory hooks for learning
- Comprehensive logging for traceability
"""

import logging
from typing import List, Dict, Optional
from datetime import date, timedelta
from enum import Enum
from copy import deepcopy
from collections import deque

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .state import CalendarizedTask, WorldState
from .validator import WorldValidator, ValidationResult
from .query import WorldQueryEngine
from app.models import ScheduledTask, CapacitySnapshot
from ..memory.semantic import SemanticMemory, MemoryPriority


class UpdateAction(str, Enum):
    """Types of update actions"""
    ADD_TASK = "add_task"
    UPDATE_TASK = "update_task" 
    REMOVE_TASK = "remove_task"
    COMPLETE_TASK = "complete_task"
    RESCHEDULE_TASK = "reschedule_task"
    APPLY_PLAN = "apply_plan" # Apply a set of tasks as a plan


class UpdateResult(BaseModel):
    """Result of a world state update operation"""
    success: bool
    action: UpdateAction
    affected_task_ids: List[str] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    capacity_changes: Dict[str, float] = Field(default_factory=dict)  # date -> new_load
    invalidated_cache_keys: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    rollback_performed: bool = False
    
    # Conflict resolution - suggest alternative slots when task can't be added
    suggested_slots: List[Dict] = Field(default_factory=list)  # Alternative time slots


class ChangeImpact(BaseModel):
    """Analysis of what needs updating when tasks change"""
    affected_dates: List[date] = Field(default_factory=list)
    affected_weeks: List[str] = Field(default_factory=list)  # ISO week strings
    conflicting_tasks: List[str] = Field(default_factory=list)  # task IDs
    capacity_recalc_needed: bool = False
    cache_invalidation_keys: List[str] = Field(default_factory=list)  # cache keys for invalidated queries
    semantic_memory_update: bool = False  # Future: trigger memory learning


class UndoOperation(BaseModel):
    """Represents an undoable operation for the undo stack"""
    operation_id: int
    action: UpdateAction
    timestamp: str
    description: str
    before_state: Dict  # Serialized state before operation
    after_state: Dict   # Serialized state after operation
    task_data: Optional[Dict] = None  # Task data for the operation


class WorldUpdater:
    """
    Central coordinator for world state maintenance.
    Keeps global task coordination system current as tasks change.
    
    Enhanced with:
    - SQLAlchemy session injection for transactional persistence
    - Comprehensive state backup with deepcopy
    - Batch validation optimization 
    - Two-way sync between in-memory and database
    - Optional logging for full traceability
    """
    
    def __init__(self, world_state: WorldState, db_session: Optional[Session] = None, logger: Optional[logging.Logger] = None, user_id: Optional[int] = None):
        self.world_state = world_state
        self.db_session = db_session
        self.validator = WorldValidator(world_state)
        self.query_engine = WorldQueryEngine(world_state)
        self._state_backup: Optional[WorldState] = None
        
        # Logging support for traceability
        self.logger = logger or logging.getLogger(__name__)
        self._operation_id = 0  # Track operation sequence
        
        # Undo stack - evolve from simple rollback logic
        self._undo_stack: deque = deque(maxlen=10)  # Keep last 10 operations
        self._current_state_snapshot: Optional[WorldState] = None
        
        # Semantic memory for learning and pattern recognition
        self.semantic_memory: Optional[SemanticMemory] = None
        if user_id:
            self.semantic_memory = SemanticMemory(user_id=user_id, db_session=self.db_session, logger=self.logger)
    
    # === CORE UPDATE METHODS ===
    
    def add_task(self, task: CalendarizedTask, persist: bool = True) -> UpdateResult:
        """
        Add a new task to the world state
        
        Args:
            task: Task to add
            persist: Whether to persist to database via SQLAlchemy
            
        Returns:
            UpdateResult with validation and impact details
        """
        self._operation_id += 1
        op_id = self._operation_id
        
        self.logger.info(f"[OP-{op_id}] Starting add_task: {task.title} ({task.start_datetime} - {task.end_datetime})")
        
        try:
            # 1. Backup current state for potential rollback and undo stack
            self._backup_state()
            self._current_state_snapshot = deepcopy(self.world_state)  # For undo stack
            self.logger.debug(f"[OP-{op_id}] State backed up for rollback and undo stack")
            
            # 2. Validate task doesn't conflict with world state
            validation_result = self.validator.validate_task(task)
            if not validation_result.is_valid:
                self.logger.warning(f"[OP-{op_id}] Task validation failed: {validation_result.conflicts}")
                
                # Conflict resolution: suggest alternative slots
                suggested_slots = self._find_alternative_slots(task)
                self.logger.info(f"[OP-{op_id}] Found {len(suggested_slots)} alternative slots")
                
                return UpdateResult(
                    success=False,
                    action=UpdateAction.ADD_TASK,
                    validation_result=validation_result,
                    error_message="Task validation failed",
                    suggested_slots=suggested_slots
                )
            
            # 3. Analyze change impact before making changes
            impact = self._analyze_change_impact(task, UpdateAction.ADD_TASK)
            
            # 4. Update in-memory world state
            self.world_state.all_tasks.append(task)
            
            # 5. Recalculate affected capacity loads
            capacity_changes = self._recalculate_capacity_load(impact.affected_dates)
            
            # 6. Persist via SQLAlchemy models (if requested)
            if persist:
                self._persist_task_addition(task)
            
            # 7. Invalidate query engine caches
            invalidated_keys = self._invalidate_caches(impact)
            
            # 8. Hook for future semantic memory updates
            if impact.semantic_memory_update:
                self._update_semantic_memory(task, UpdateAction.ADD_TASK)
            
            # 9. Add to undo stack for future undo operations
            self._push_to_undo_stack(
                UpdateAction.ADD_TASK,
                f"Added task: {task.title}",
                task_data=task.dict()
            )
            
            self.logger.info(f"[OP-{op_id}] Successfully added task: {task.title}")
            
            return UpdateResult(
                success=True,
                action=UpdateAction.ADD_TASK,
                affected_task_ids=[task.task_id],
                validation_result=validation_result,
                capacity_changes=capacity_changes,
                invalidated_cache_keys=invalidated_keys
            )
            
        except Exception as e:
            self._rollback_state()
            return UpdateResult(
                success=False,
                action=UpdateAction.ADD_TASK,
                error_message=f"Add task failed: {str(e)}",
                rollback_performed=True
            )
    
    def remove_task(self, task_id: str, persist: bool = True) -> UpdateResult:
        """
        Remove a task from the world state
        
        Args:
            task_id: ID of task to remove
            persist: Whether to persist removal to database
            
        Returns:
            UpdateResult with impact details
        """
        try:
            # 1. Find the task to remove
            task_to_remove = None
            for task in self.world_state.all_tasks:
                if task.task_id == task_id:
                    task_to_remove = task
                    break
            
            if not task_to_remove:
                return UpdateResult(
                    success=False,
                    action=UpdateAction.REMOVE_TASK,
                    error_message=f"Task {task_id} not found"
                )
            
            # 2. Backup state
            self._backup_state()
            
            # 3. Analyze impact
            impact = self._analyze_change_impact(task_to_remove, UpdateAction.REMOVE_TASK)
            
            # 4. Remove from in-memory state
            self.world_state.all_tasks = [t for t in self.world_state.all_tasks if t.task_id != task_id]
            
            # 5. Recalculate capacity
            capacity_changes = self._recalculate_capacity_load(impact.affected_dates)
            
            # 6. Persist removal
            if persist:
                self._persist_task_removal(task_id)
            
            # 7. Invalidate caches
            invalidated_keys = self._invalidate_caches(impact)
            
            # 8. Semantic memory hook
            if impact.semantic_memory_update:
                self._update_semantic_memory(task_to_remove, UpdateAction.REMOVE_TASK)
            
            return UpdateResult(
                success=True,
                action=UpdateAction.REMOVE_TASK,
                affected_task_ids=[task_id],
                capacity_changes=capacity_changes,
                invalidated_cache_keys=invalidated_keys
            )
            
        except Exception as e:
            self._rollback_state()
            return UpdateResult(
                success=False,
                action=UpdateAction.REMOVE_TASK,
                error_message=f"Remove task failed: {str(e)}",
                rollback_performed=True
            )
    
    def update_task(self, updated_task: CalendarizedTask, persist: bool = True) -> UpdateResult:
        """
        Update an existing task in the world state
        
        Args:
            updated_task: Task with updated information
            persist: Whether to persist changes to database
            
        Returns:
            UpdateResult with validation and impact details
        """
        try:
            # 1. Find existing task
            existing_task = None
            for i, task in enumerate(self.world_state.all_tasks):
                if task.task_id == updated_task.task_id:
                    existing_task = task
                    break
            
            if not existing_task:
                return UpdateResult(
                    success=False,
                    action=UpdateAction.UPDATE_TASK,
                    error_message=f"Task {updated_task.task_id} not found"
                )
            
            # 2. Backup state
            self._backup_state()
            
            # 3. Validate updated task
            validation_result = self.validator.validate_task(updated_task)
            if not validation_result.is_valid:
                return UpdateResult(
                    success=False,
                    action=UpdateAction.UPDATE_TASK,
                    validation_result=validation_result,
                    error_message="Updated task validation failed"
                )
            
            # 4. Analyze impact of both old and new task
            old_impact = self._analyze_change_impact(existing_task, UpdateAction.REMOVE_TASK)
            new_impact = self._analyze_change_impact(updated_task, UpdateAction.ADD_TASK)
            combined_impact = self._merge_impacts(old_impact, new_impact)
            
            # 5. Update in-memory state
            for i, task in enumerate(self.world_state.all_tasks):
                if task.task_id == updated_task.task_id:
                    self.world_state.all_tasks[i] = updated_task
                    break
            
            # 6. Recalculate capacity
            capacity_changes = self._recalculate_capacity_load(combined_impact.affected_dates)
            
            # 7. Persist changes
            if persist:
                self._persist_task_update(updated_task)
            
            # 8. Invalidate caches
            invalidated_keys = self._invalidate_caches(combined_impact)
            
            # 9. Semantic memory hook
            if combined_impact.semantic_memory_update:
                self._update_semantic_memory(updated_task, UpdateAction.UPDATE_TASK)
            
            return UpdateResult(
                success=True,
                action=UpdateAction.UPDATE_TASK,
                affected_task_ids=[updated_task.task_id],
                validation_result=validation_result,
                capacity_changes=capacity_changes,
                invalidated_cache_keys=invalidated_keys
            )
            
        except Exception as e:
            self._rollback_state()
            return UpdateResult(
                success=False,
                action=UpdateAction.UPDATE_TASK,
                error_message=f"Update task failed: {str(e)}",
                rollback_performed=True
            )
    
    def apply_plan(self, tasks: List[CalendarizedTask], persist: bool = True) -> UpdateResult:
        """
        Apply a complete plan (multiple tasks) to the world state with enhanced batch processing
        
        Args:
            tasks: List of tasks to add to world state
            persist: Whether to persist all tasks to database
            
        Returns:
            UpdateResult with batch operation details
        """
        if not tasks:
            return UpdateResult(
                success=True,
                action=UpdateAction.APPLY_PLAN,
                affected_task_ids=[],
                error_message="No tasks to apply"
            )
        
        try:
            # 1. Backup state
            self._backup_state()
            
            # 2. Enhanced batch validation: check both world conflicts AND internal conflicts
            # First validate each task against current world state
            validation_results = self.validator.validate_task_list(tasks)
            invalid_tasks = [task_id for task_id, result in validation_results.items() if not result.is_valid]
            
            # Additional: Check for internal conflicts within the new task set
            internal_conflicts = self._check_plan_internal_conflicts(tasks)
            if internal_conflicts:
                invalid_tasks.extend(internal_conflicts.keys())
            
            if invalid_tasks:
                return UpdateResult(
                    success=False,
                    action=UpdateAction.APPLY_PLAN,
                    affected_task_ids=list(set(invalid_tasks)),  # Remove duplicates
                    error_message=f"Plan validation failed for tasks: {invalid_tasks}"
                )
            
            # 3. Analyze combined impact
            all_impacts = [self._analyze_change_impact(task, UpdateAction.ADD_TASK) for task in tasks]
            combined_impact = self._merge_multiple_impacts(all_impacts)
            
            # 4. Apply to in-memory state first
            self.world_state.all_tasks.extend(tasks)
            
            # 5. Recalculate capacity for all affected dates
            capacity_changes = self._recalculate_capacity_load(combined_impact.affected_dates)
            
            # 6. Transactional persistence with rollback capability
            if persist and self.db_session:
                try:
                    self._persist_plan_application_transactional(tasks, capacity_changes)
                except Exception as db_error:
                    self._rollback_state()
                    return UpdateResult(
                        success=False,
                        action=UpdateAction.APPLY_PLAN,
                        error_message=f"Database persistence failed: {str(db_error)}",
                        rollback_performed=True
                    )
            
            # 7. Invalidate caches
            invalidated_keys = self._invalidate_caches(combined_impact)
            
            # 8. Semantic memory hook for plan patterns
            if combined_impact.semantic_memory_update:
                self._update_semantic_memory_for_plan(tasks)
            
            return UpdateResult(
                success=True,
                action=UpdateAction.APPLY_PLAN,
                affected_task_ids=[task.task_id for task in tasks],
                capacity_changes=capacity_changes,
                invalidated_cache_keys=invalidated_keys
            )
            
        except Exception as e:
            self._rollback_state()
            return UpdateResult(
                success=False,
                action=UpdateAction.APPLY_PLAN,
                error_message=f"Apply plan failed: {str(e)}",
                rollback_performed=True
            )
    
    # === INTERNAL HELPER METHODS ===
    
    def _backup_state(self) -> None:
        """Create comprehensive backup of current world state for rollback"""
        # Use deepcopy to ensure complete isolation of backup state
        # Covers all fields including availability, capacity, blackouts
        self._state_backup = deepcopy(self.world_state)
    
    def _rollback_state(self) -> None:
        """Restore world state from comprehensive backup"""
        if self._state_backup:
            # Restore all state fields, not just tasks and capacity
            self.world_state.all_tasks = self._state_backup.all_tasks
            self.world_state.capacity = self._state_backup.capacity
            self.world_state.availability = self._state_backup.availability
            self.world_state.blackouts = self._state_backup.blackouts
            self.world_state.last_updated = self._state_backup.last_updated
    
    def _analyze_change_impact(self, task: CalendarizedTask, action: UpdateAction) -> ChangeImpact:
        """Analyze what needs updating when a task changes"""
        impact = ChangeImpact()
        
        # Affected dates
        task_date = task.start_datetime.date()
        impact.affected_dates.append(task_date)
        
        # Affected weeks
        week_start = task_date - timedelta(days=task_date.weekday())
        week_key = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"
        impact.affected_weeks.append(week_key)
        
        # Check for conflicting tasks
        for existing_task in self.world_state.all_tasks:
            if existing_task.task_id != task.task_id:
                if self._tasks_overlap(task, existing_task):
                    impact.conflicting_tasks.append(existing_task.task_id)
        
        # Always need capacity recalculation
        impact.capacity_recalc_needed = True
        
        # Cache keys to invalidate
        impact.cache_invalidation_keys = [
            f"slots_{task_date.isoformat()}",
            f"availability_{task_date.isoformat()}",
            f"capacity_{week_key}"
        ]
        
        # Future: semantic memory trigger
        impact.semantic_memory_update = action in [UpdateAction.ADD_TASK, UpdateAction.APPLY_PLAN]
        
        return impact
    
    def _recalculate_capacity_load(self, affected_dates: List[date]) -> Dict[str, float]:
        """Recalculate daily and weekly capacity loads"""
        capacity_changes = {}
        
        # Recalculate daily loads
        for affected_date in affected_dates:
            date_str = affected_date.isoformat()
            total_hours = 0.0
            
            for task in self.world_state.all_tasks:
                if task.start_datetime.date() == affected_date:
                    total_hours += task.estimated_minutes / 60.0
            
            self.world_state.capacity.current_daily_load[date_str] = total_hours
            capacity_changes[date_str] = total_hours
        
        # Recalculate weekly loads
        processed_weeks = set()
        for affected_date in affected_dates:
            week_start = affected_date - timedelta(days=affected_date.weekday())
            week_key = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"
            
            if week_key not in processed_weeks:
                total_hours = 0.0
                week_end = week_start + timedelta(days=7)
                
                for task in self.world_state.all_tasks:
                    task_date = task.start_datetime.date()
                    if week_start <= task_date < week_end:
                        total_hours += task.estimated_minutes / 60.0
                
                self.world_state.capacity.current_weekly_load[week_key] = total_hours
                capacity_changes[f"week_{week_key}"] = total_hours
                processed_weeks.add(week_key)
        
        return capacity_changes
    
    def _invalidate_caches(self, impact: ChangeImpact) -> List[str]:
        """
        Return the cache keys that would be invalidated for affected time periods.
        (Actual cache invalidation logic to be implemented when query engine supports caching.)
        """
        # Future: when query engine has caching, clear relevant caches
        # For now, just return the keys that would be invalidated
        return impact.cache_invalidation_keys
    
    def _tasks_overlap(self, task1: CalendarizedTask, task2: CalendarizedTask) -> bool:
        """Check if two tasks have overlapping time"""
        return (task1.start_datetime < task2.end_datetime and 
                task2.start_datetime < task1.end_datetime)
    
    def _merge_impacts(self, impact1: ChangeImpact, impact2: ChangeImpact) -> ChangeImpact:
        """Merge two change impacts into one"""
        return ChangeImpact(
            affected_dates=list(set(impact1.affected_dates + impact2.affected_dates)),
            affected_weeks=list(set(impact1.affected_weeks + impact2.affected_weeks)),
            conflicting_tasks=list(set(impact1.conflicting_tasks + impact2.conflicting_tasks)),
            capacity_recalc_needed=impact1.capacity_recalc_needed or impact2.capacity_recalc_needed,
            cache_invalidation_keys=list(set(impact1.cache_invalidation_keys + impact2.cache_invalidation_keys)),
            semantic_memory_update=impact1.semantic_memory_update or impact2.semantic_memory_update
        )
    
    def _merge_multiple_impacts(self, impacts: List[ChangeImpact]) -> ChangeImpact:
        """Merge multiple change impacts into one"""
        if not impacts:
            return ChangeImpact()
        
        result = impacts[0]
        for impact in impacts[1:]:
            result = self._merge_impacts(result, impact)
        
        return result
    
    def _check_plan_internal_conflicts(self, tasks: List[CalendarizedTask]) -> Dict[str, List[str]]:
        """
        Check for conflicts within the new task set itself
        Enhanced batch validation for apply_plan
        """
        conflicts = {}
        
        for i, task1 in enumerate(tasks):
            task_conflicts = []
            for j, task2 in enumerate(tasks):
                if i != j and self._tasks_overlap(task1, task2):
                    task_conflicts.append(f"Internal conflict with task: {task2.title}")
            
            if task_conflicts:
                conflicts[task1.task_id] = task_conflicts
        
        return conflicts
    
    # === PERSISTENCE METHODS (SQLAlchemy Integration) ===
    
    def _persist_task_addition(self, task: CalendarizedTask) -> None:
        """Persist new scheduled task to database via ScheduledTask ORM"""
        if not self.db_session:
            return  # No persistence without session
        
        try:
            # Convert CalendarizedTask to ScheduledTask ORM
            # Note: We need user_id, plan_id, and task_id from context
            user_id = int(self.world_state.user_id)
            plan_id = int(task.plan_id)
            task_id = int(task.task_id) if task.task_id.isdigit() else None
            
            if task_id is None:
                # This is a generated task, we'll need to handle it differently
                # For now, skip persistence of generated tasks
                return
            
            scheduled_task = ScheduledTask.from_calendarized_task(
                task, user_id=user_id, plan_id=plan_id, task_id=task_id
            )
            self.db_session.add(scheduled_task)
            self.db_session.flush()  # Flush but don't commit yet
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def _persist_task_removal(self, task_id: str) -> None:
        """Persist scheduled task removal to database"""
        if not self.db_session:
            return
        
        try:
            scheduled_task = self.db_session.query(ScheduledTask).filter_by(id=task_id).first()
            if scheduled_task:
                self.db_session.delete(scheduled_task)
                self.db_session.flush()
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def _persist_task_update(self, task: CalendarizedTask) -> None:
        """Persist scheduled task update to database"""
        if not self.db_session:
            return
        
        try:
            import json
            
            # Execute bulk update using column references
            self.db_session.query(ScheduledTask).filter_by(id=task.task_id).update({
                ScheduledTask.start_datetime: task.start_datetime,
                ScheduledTask.end_datetime: task.end_datetime,
                ScheduledTask.estimated_minutes: task.estimated_minutes,
                ScheduledTask.title: task.title,
                ScheduledTask.status: task.status,
                ScheduledTask.priority: task.priority,
                ScheduledTask.notes: task.notes,
                ScheduledTask.tags: json.dumps(task.tags) if task.tags else None
            })
            self.db_session.flush()
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def _persist_plan_application(self, tasks: List[CalendarizedTask]) -> None:
        """Persist entire plan to database (legacy method)"""
        if not self.db_session:
            return
        
        try:
            for task in tasks:
                self._persist_task_addition(task)
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    def _persist_plan_application_transactional(self, tasks: List[CalendarizedTask], 
                                               capacity_changes: Dict[str, float]) -> None:
        """
        Enhanced transactional persistence for plan application
        Handles scheduled tasks and creates capacity snapshots
        """
        if not self.db_session:
            return
        
        try:
            with self.db_session.begin():  # Transaction context
                # 1. Persist all scheduled tasks
                for task in tasks:
                    self._persist_task_addition(task)
                
                # 2. Create capacity snapshot for analytics
                self._create_capacity_snapshot(capacity_changes)
                
                # 3. Auto-commit on success, auto-rollback on exception
                
        except Exception as e:
            # Transaction will auto-rollback
            raise e
    
    def _create_capacity_snapshot(self, capacity_changes: Dict[str, float]) -> None:
        """Create capacity snapshot for historical analytics"""
        if not self.db_session:
            return
        
        user_id = int(self.world_state.user_id)
        
        # Create snapshots for each period with changes
        for period_key, scheduled_hours in capacity_changes.items():
            if period_key.startswith('week_'):
                period_type = "weekly"
                clean_period_key = period_key.replace('week_', '')
                limit_hours = self.world_state.capacity.constraints.max_hours_per_week
            else:
                period_type = "daily"
                clean_period_key = period_key
                limit_hours = self.world_state.capacity.constraints.max_hours_per_day
            
            # Create capacity snapshot
            snapshot = CapacitySnapshot(
                user_id=user_id,
                period_type=period_type,
                period_key=clean_period_key,
                limit_hours=limit_hours,
                scheduled_hours=scheduled_hours,
                utilization_rate=scheduled_hours / limit_hours if limit_hours > 0 else 0.0
            )
            self.db_session.add(snapshot)
    
    def _calculate_capacity_changes(self, tasks: List[CalendarizedTask]) -> Dict[str, float]:
        """
        Calculate capacity load changes from a set of tasks
        Returns dict mapping period keys to load hours
        """
        daily_changes = {}
        weekly_changes = {}
        
        for task in tasks:
            task_date = task.start_datetime.date()
            task_hours = task.estimated_minutes / 60.0
            
            # Daily capacity change
            date_str = task_date.isoformat()
            daily_changes[date_str] = daily_changes.get(date_str, 0.0) + task_hours
            
            # Weekly capacity change
            week_start = task_date - timedelta(days=task_date.weekday())
            week_key = f"week_{week_start.year}-W{week_start.isocalendar()[1]:02d}"
            weekly_changes[week_key] = weekly_changes.get(week_key, 0.0) + task_hours
        
        # Combine both daily and weekly changes
        all_changes = {}
        all_changes.update(daily_changes)
        all_changes.update(weekly_changes)
        
        return all_changes
    
    def sync_from_database(self) -> None:
        """
        Sync world state from database (pull fresh data)
        Rebuilds CalendarizedTask list from ScheduledTask records
        """
        if not self.db_session:
            return
        
        user_id = int(self.world_state.user_id)
        
        # Pull all scheduled tasks for this user from database
        scheduled_tasks = self.db_session.query(ScheduledTask).filter_by(user_id=user_id).all()
        
        # Convert to CalendarizedTask models and update world state
        fresh_tasks = [scheduled_task.to_calendarized_task() for scheduled_task in scheduled_tasks]
        self.world_state.all_tasks = fresh_tasks
        
        # Recalculate capacity loads from fresh data
        self._recalculate_all_capacity_loads()
    
    def _recalculate_all_capacity_loads(self) -> None:
        """Recalculate all capacity loads from current task set"""
        # Clear existing loads
        self.world_state.capacity.current_daily_load.clear()
        self.world_state.capacity.current_weekly_load.clear()
        
        # Group tasks by date and week
        daily_loads = {}
        weekly_loads = {}
        
        for task in self.world_state.all_tasks:
            task_date = task.start_datetime.date()
            task_hours = task.estimated_minutes / 60.0
            
            # Daily load
            date_str = task_date.isoformat()
            daily_loads[date_str] = daily_loads.get(date_str, 0.0) + task_hours
            
            # Weekly load
            week_start = task_date - timedelta(days=task_date.weekday())
            week_key = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"
            weekly_loads[week_key] = weekly_loads.get(week_key, 0.0) + task_hours
        
        # Update world state
        self.world_state.capacity.current_daily_load.update(daily_loads)
        self.world_state.capacity.current_weekly_load.update(weekly_loads)
    
    # === SEMANTIC MEMORY HOOKS (Future: Step 2.5) ===
    
    def _update_semantic_memory(self, task: CalendarizedTask, action: UpdateAction) -> None:
        """Update semantic memory for learning patterns"""
        if not self.semantic_memory:
            return
        
        # Log the operation with context
        operation_data = {
            "operation_type": action.value,
            "task_id": task.task_id,
            "task_title": task.title,
            "task_category": getattr(task, 'category', 'general'),
            "duration_minutes": (task.end_datetime - task.start_datetime).total_seconds() / 60,
            "scheduled_time": task.start_datetime.isoformat(),
            "day_of_week": task.start_datetime.strftime("%A"),
            "time_of_day": task.start_datetime.strftime("%H:%M"),
            "related_entities": {
                "task_id": task.task_id,
                "goal_id": getattr(task, 'goal_id', None)
            }
        }
        
        memory_id = self.semantic_memory.log_operation(
            operation_type=action.value,
            details=operation_data,
            priority=MemoryPriority.MEDIUM
        )
        
        self.logger.debug(f"Logged semantic memory: {action.value} -> {memory_id}")
    
    def _update_semantic_memory_for_plan(self, tasks: List[CalendarizedTask]) -> None:
        """Update semantic memory for plan-level patterns"""
        if not self.semantic_memory:
            return
        
        # Log plan-level insights
        plan_data = {
            "operation_type": "apply_plan",
            "plan_size": len(tasks),
            "task_categories": [getattr(task, 'category', 'general') for task in tasks],
            "time_span_hours": self._calculate_plan_timespan(tasks),
            "task_ids": [task.task_id for task in tasks],
            "planned_dates": [task.start_datetime.date().isoformat() for task in tasks],
            "related_entities": {
                "task_ids": [task.task_id for task in tasks]
            }
        }
        
        memory_id = self.semantic_memory.log_operation(
            operation_type="apply_plan",
            details=plan_data,
            priority=MemoryPriority.HIGH  # Plans are important for learning user patterns
        )
        
        self.logger.debug(f"Logged plan semantic memory: apply_plan -> {memory_id}")
    
    def _calculate_plan_timespan(self, tasks: List[CalendarizedTask]) -> float:
        """Calculate total timespan of a plan in hours"""
        if not tasks:
            return 0.0
        
        start_times = [task.start_datetime for task in tasks]
        end_times = [task.end_datetime for task in tasks]
        
        earliest = min(start_times)
        latest = max(end_times)
        
        return (latest - earliest).total_seconds() / 3600
    
    # === CONFLICT RESOLUTION ===
    
    def _find_alternative_slots(self, task: CalendarizedTask, max_suggestions: int = 5) -> List[Dict]:
        """
        Find alternative time slots when a task can't be scheduled.
        Uses query.py to find available slots with same duration.
        
        Args:
            task: The task that couldn't be scheduled
            max_suggestions: Maximum number of alternative slots to return
            
        Returns:
            List of suggested slots with start_time, end_time, and reason
        """
        self.logger.debug(f"Finding alternative slots for task: {task.title}")
        
        # Calculate task duration
        duration_minutes = task.estimated_minutes
        
        # Use query engine to find available slots
        # Look for slots within the next 7 days from original start date
        search_start = task.start_datetime.date()
        search_end = search_start + timedelta(days=7)
        
        try:
            # Create a slot query with the required parameters
            from .query import SlotQuery
            slot_query = SlotQuery(
                duration_minutes=duration_minutes,
                start_date=search_start,
                end_date=search_end,
                max_results=max_suggestions
            )
            
            # Query for available slots with the same duration
            slot_result = self.query_engine.find_available_slots(slot_query)
            available_slots = slot_result.slots
            
            suggestions = []
            for slot in available_slots[:max_suggestions]:
                # Convert to suggestion format
                suggestion = {
                    "start_datetime": slot.start_datetime.isoformat(),
                    "end_datetime": slot.end_datetime.isoformat(),
                    "duration_minutes": duration_minutes,
                    "reason": f"Available slot on {slot.start_datetime.strftime('%A, %B %d')}",
                    "confidence": 0.9  # High confidence for exact matches
                }
                suggestions.append(suggestion)
                
            self.logger.info(f"Found {len(suggestions)} alternative slots")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error finding alternative slots: {e}")
            return []
    
    # === UNDO STACK FUNCTIONALITY ===
    
    def _push_to_undo_stack(self, action: UpdateAction, description: str, task_data: Optional[Dict] = None) -> None:
        """Push current operation to undo stack"""
        from datetime import datetime
        
        undo_op = UndoOperation(
            operation_id=self._operation_id,
            action=action,
            timestamp=datetime.now().isoformat(),
            description=description,
            before_state=self._current_state_snapshot.dict() if self._current_state_snapshot else {},
            after_state=self.world_state.dict(),
            task_data=task_data
        )
        
        self._undo_stack.append(undo_op)
        self.logger.debug(f"[OP-{self._operation_id}] Pushed to undo stack: {description}")
    
    def undo_last_operation(self) -> UpdateResult:
        """
        Undo the last operation from the undo stack
        
        Returns:
            UpdateResult indicating success/failure of undo operation
        """
        if not self._undo_stack:
            self.logger.warning("No operations to undo")
            return UpdateResult(
                success=False,
                action=UpdateAction.REMOVE_TASK,  # Generic action for undo
                error_message="No operations available to undo"
            )
        
        try:
            # Get the last operation
            last_op = self._undo_stack.pop()
            self.logger.info(f"Undoing operation {last_op.operation_id}: {last_op.description}")
            
            # Restore the before state
            before_state_dict = last_op.before_state
            restored_state = WorldState(**before_state_dict)
            
            # Replace current state
            self.world_state.all_tasks = restored_state.all_tasks
            self.world_state.availability = restored_state.availability
            self.world_state.capacity = restored_state.capacity
            self.world_state.blackouts = restored_state.blackouts
            self.world_state.user_id = restored_state.user_id
            
            # Invalidate caches since state changed
            self.query_engine._task_cache.clear()
            
            self.logger.info(f"Successfully undid operation {last_op.operation_id}")
            
            return UpdateResult(
                success=True,
                action=UpdateAction.REMOVE_TASK,  # Represents undo action
                error_message=f"Undid: {last_op.description}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to undo operation: {e}")
            return UpdateResult(
                success=False,
                action=UpdateAction.REMOVE_TASK,
                error_message=f"Undo failed: {str(e)}"
            )
    
    def get_undo_history(self) -> List[Dict]:
        """Get the history of undoable operations"""
        return [
            {
                "operation_id": op.operation_id,
                "action": op.action,
                "timestamp": op.timestamp,
                "description": op.description
            }
            for op in self._undo_stack
        ]


# === CONVENIENCE FUNCTIONS ===

def update_world_state(world_state: WorldState, action: UpdateAction, **kwargs) -> UpdateResult:
    """
    Convenience function for world state updates
    
    Args:
        world_state: Current world state
        action: Type of update to perform
        **kwargs: Action-specific parameters
        
    Returns:
        UpdateResult with operation details
    """
    updater = WorldUpdater(world_state)
    
    if action == UpdateAction.ADD_TASK:
        task = kwargs.get('task')
        if not task:
            return UpdateResult(
                success=False,
                action=action,
                error_message="Task parameter required for ADD_TASK"
            )
        persist = kwargs.get('persist', True)
        return updater.add_task(task, persist)
    
    elif action == UpdateAction.REMOVE_TASK:
        task_id = kwargs.get('task_id')
        if not task_id:
            return UpdateResult(
                success=False,
                action=action,
                error_message="task_id parameter required for REMOVE_TASK"
            )
        persist = kwargs.get('persist', True)
        return updater.remove_task(task_id, persist)
    
    elif action == UpdateAction.UPDATE_TASK:
        task = kwargs.get('task')
        if not task:
            return UpdateResult(
                success=False,
                action=action,
                error_message="Task parameter required for UPDATE_TASK"
            )
        persist = kwargs.get('persist', True)
        return updater.update_task(task, persist)
    
    elif action == UpdateAction.APPLY_PLAN:
        tasks = kwargs.get('tasks')
        if not tasks:
            return UpdateResult(
                success=False,
                action=action,
                error_message="tasks parameter required for APPLY_PLAN"
            )
        persist = kwargs.get('persist', True)
        return updater.apply_plan(tasks, persist)
    
    else:
        return UpdateResult(
            success=False,
            action=action,
            error_message=f"Unsupported action: {action}"
        )


def create_world_updater(world_state: WorldState) -> WorldUpdater:
    """Factory function to create a world updater"""
    return WorldUpdater(world_state)
