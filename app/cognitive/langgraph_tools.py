"""
LangGraph Tool Wrappers for Smart Personal Planner

Exposes WorldUpdater operations as LangGraph tools with full observability.
This enables the AI agent to interact with the planning system while maintaining
complete traceability and learning from interactions.

Features:
- Tool exposure for add_task, remove_task, apply_plan operations
- Rich metadata collection for observability
- Integration with semantic memory for learning
- Error handling and validation
- Performance metrics and timing
"""

import logging
import time
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from functools import wraps

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .world.updater import WorldUpdater
from .world.state import CalendarizedTask
from memory.semantic import SemanticMemory, MemoryPriority


# === TOOL INPUT SCHEMAS ===

class AddTaskInput(BaseModel):
    """Input schema for add_task tool"""
    task_id: str = Field(description="Unique identifier for the task")
    title: str = Field(description="Task title/description")
    start_datetime: str = Field(description="Start datetime in ISO format")
    end_datetime: str = Field(description="End datetime in ISO format") 
    category: Optional[str] = Field(default="general", description="Task category")
    priority: Optional[str] = Field(default="medium", description="Task priority")
    description: Optional[str] = Field(default="", description="Detailed task description")
    goal_id: Optional[str] = Field(default=None, description="Associated goal ID")


class RemoveTaskInput(BaseModel):
    """Input schema for remove_task tool"""
    task_id: str = Field(description="ID of task to remove")
    reason: Optional[str] = Field(default="", description="Reason for removal")


class ApplyPlanInput(BaseModel):
    """Input schema for apply_plan tool"""
    tasks: List[Dict] = Field(description="List of task dictionaries to add as a plan")
    plan_name: Optional[str] = Field(default="", description="Name of the plan")
    plan_description: Optional[str] = Field(default="", description="Plan description")


# === OBSERVABILITY DECORATORS ===

def with_observability(semantic_memory: Optional[SemanticMemory] = None, logger: Optional[logging.Logger] = None):
    """
    Decorator to add observability metadata to tool operations.
    
    Captures:
    - Execution timing
    - Input/output data
    - Success/failure status
    - Performance metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            start_time = time.time()
            operation_id = f"{func.__name__}_{int(start_time * 1000)}"
            
            # Set up logging
            log = logger or logging.getLogger(__name__)
            log.info(f"[TOOL-{operation_id}] Starting {func.__name__}")
            
            try:
                # Execute the actual tool function
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log successful execution
                log.info(f"[TOOL-{operation_id}] Completed {func.__name__} in {execution_time:.3f}s")
                
                # Log to semantic memory if available
                if semantic_memory:
                    memory_data = {
                        "tool_name": func.__name__,
                        "execution_time_seconds": execution_time,
                        "success": result.get("success", True),
                        "input_args": str(args)[:500],  # Truncate long inputs
                        "input_kwargs": str(kwargs)[:500],
                        "result_summary": str(result)[:500],
                        "operation_id": operation_id
                    }
                    
                    semantic_memory.log_operation(
                        operation_type=f"langgraph_tool_{func.__name__}",
                        details=memory_data,
                        priority=MemoryPriority.MEDIUM
                    )
                
                # Add observability metadata to result
                if isinstance(result, dict):
                    result["_observability"] = {
                        "operation_id": operation_id,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat(),
                        "tool_name": func.__name__
                    }
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                log.error(f"[TOOL-{operation_id}] Failed {func.__name__} after {execution_time:.3f}s: {str(e)}")
                
                # Log failure to semantic memory
                if semantic_memory:
                    error_data = {
                        "tool_name": func.__name__,
                        "execution_time_seconds": execution_time,
                        "success": False,
                        "error_message": str(e),
                        "error_type": type(e).__name__,
                        "operation_id": operation_id
                    }
                    
                    semantic_memory.log_operation(
                        operation_type=f"langgraph_tool_error_{func.__name__}",
                        details=error_data,
                        priority=MemoryPriority.HIGH  # Errors are important for learning
                    )
                
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "_observability": {
                        "operation_id": operation_id,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat(),
                        "tool_name": func.__name__
                    }
                }
        
        return wrapper
    return decorator


# === LANGGRAPH TOOL CLASSES ===

class AddTaskTool(BaseTool):
    """LangGraph tool for adding tasks to the planning system"""
    
    name: str = "add_task"
    description: str = """
    Add a new task to the personal planning system.
    
    This tool schedules a new task at the specified time, validates it doesn't conflict
    with existing tasks, and updates the world state. If conflicts are detected,
    alternative time slots will be suggested.
    
    Returns success status, validation results, and any suggested alternatives.
    """
    args_schema: type[BaseModel] = AddTaskInput

    def __init__(self, world_updater: WorldUpdater, semantic_memory: Optional[SemanticMemory] = None, logger: Optional[logging.Logger] = None):
        super().__init__()
        self.world_updater = world_updater
        self.semantic_memory = semantic_memory
        self.logger = logger or logging.getLogger(__name__)
    
    @with_observability()
    def _run(self, task_id: str, title: str, start_datetime: str, end_datetime: str, 
             category: str = "general", priority: str = "medium", description: str = "", 
             goal_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the add_task operation"""
        
        try:
            # Parse datetime strings
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            # Convert priority string to integer (example mapping)
            priority_map = {"low": 1, "medium": 2, "high": 3}
            priority_int = priority_map.get(priority.lower(), 2) if isinstance(priority, str) else priority

            # Create CalendarizedTask
            task = CalendarizedTask(
                task_id=task_id,
                title=title,
                start_datetime=start_dt,
                end_datetime=end_dt,
                plan_id="",
                estimated_minutes=0,
                priority=priority_int,
                goal_id=goal_id if goal_id is not None else ""
            )
            
            # Execute via WorldUpdater
            result = self.world_updater.add_task(task, persist=True)
            
            # Convert UpdateResult to dict for tool response
            response = {
                "success": result.success,
                "action": result.action.value,
                "task_id": task_id,
                "validation_passed": result.validation_result.is_valid if result.validation_result else True,
                "suggested_alternatives": result.suggested_slots or []
            }
            
            if not result.success:
                response["error"] = result.error_message
                response["rollback_performed"] = getattr(result, 'rollback_performed', False)
            
            # Log to semantic memory with decision context
            if self.semantic_memory and result.success:
                decision_context = {
                    "task_data": task.dict(),
                    "chosen_time": start_datetime,
                    "alternatives_available": len(result.suggested_slots or []),
                    "category": category,
                    "priority": priority
                }
                
                self.semantic_memory.log_ai_decision(
                    decision_context=decision_context,
                    reasoning=f"Successfully scheduled task '{title}' at {start_datetime}",
                    alternatives_considered=result.suggested_slots
                )
            
            return response
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"AddTaskTool execution failed: {str(e)}")
            else:
                logging.getLogger(__name__).error(f"AddTaskTool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


class RemoveTaskTool(BaseTool):
    """LangGraph tool for removing tasks from the planning system"""
    
    name: str = "remove_task"
    description: str = """
    Remove a task from the personal planning system.
    
    This tool removes the specified task, updates capacity calculations,
    and maintains world state consistency. The operation can be undone
    if needed using the undo functionality.
    
    Returns success status and details of the removal.
    """
    args_schema: type[BaseModel] = RemoveTaskInput
    
    def __init__(self, world_updater: WorldUpdater, semantic_memory: Optional[SemanticMemory] = None, logger: Optional[logging.Logger] = None):
        super().__init__()
        self.world_updater = world_updater
        self.semantic_memory = semantic_memory
        self.logger = logger or logging.getLogger(__name__)
    
    @with_observability()
    def _run(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        """Execute the remove_task operation"""
        
        try:
            # Execute via WorldUpdater
            result = self.world_updater.remove_task(task_id, persist=True)
            
            # Convert UpdateResult to dict for tool response
            response = {
                "success": result.success,
                "action": result.action.value,
                "task_id": task_id,
                "removal_reason": reason
            }
            
            if not result.success:
                response["error"] = result.error_message
                response["rollback_performed"] = getattr(result, 'rollback_performed', False)
            else:
                response["affected_dates"] = getattr(result, 'affected_dates', [])
            
            # Log to semantic memory
            if self.semantic_memory:
                operation_data = {
                    "task_id": task_id,
                    "removal_reason": reason,
                    "success": result.success,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.semantic_memory.log_operation(
                    operation_type="remove_task_via_tool",
                    details=operation_data,
                    priority=MemoryPriority.MEDIUM
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"RemoveTaskTool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


class ApplyPlanTool(BaseTool):
    """LangGraph tool for applying a complete plan (multiple tasks) to the planning system"""
    
    name: str = "apply_plan"
    description: str = """
    Apply a complete plan consisting of multiple tasks to the planning system.
    
    This tool adds multiple tasks as a coordinated plan, validates the entire
    plan for conflicts, and provides comprehensive feedback on the plan's
    feasibility. If conflicts exist, it suggests modifications or alternatives.
    
    Returns success status, validation results for each task, and overall plan metrics.
    """
    args_schema: type[BaseModel] = ApplyPlanInput
    
    def __init__(self, world_updater: WorldUpdater, semantic_memory: Optional[SemanticMemory] = None, logger: Optional[logging.Logger] = None):
        super().__init__()
        self.world_updater = world_updater
        self.semantic_memory = semantic_memory
        self.logger = logger or logging.getLogger(__name__)
    
    @with_observability()
    def _run(self, tasks: List[Dict], plan_name: str = "", plan_description: str = "") -> Dict[str, Any]:
        """Execute the apply_plan operation"""
        
        try:
            # Convert task dicts to CalendarizedTask objects
            calendarzied_tasks = []
            for task_data in tasks:
                start_dt = datetime.fromisoformat(task_data['start_datetime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(task_data['end_datetime'].replace('Z', '+00:00'))
                
                task = CalendarizedTask(
                    task_id=task_data['task_id'],
                    title=task_data['title'],
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    plan_id="",
                    estimated_minutes=0,
                    priority=task_data.get('priority', 'medium'),
                    goal_id=str(task_data.get('goal_id')) if task_data.get('goal_id') is not None else ""
                )
                calendarzied_tasks.append(task)
            
            # Execute via WorldUpdater
            result = self.world_updater.apply_plan(calendarzied_tasks, persist=True)
            
            # Convert UpdateResult to dict for tool response
            response = {
                "success": result.success,
                "action": result.action.value,
                "plan_name": plan_name,
                "plan_description": plan_description,
                "tasks_count": len(tasks),
                "tasks_added": getattr(result, 'tasks_added', 0),
                "validation_passed": result.validation_result.is_valid if result.validation_result else True
            }
            
            if not result.success:
                response["error"] = result.error_message
                response["rollback_performed"] = getattr(result, 'rollback_performed', False)
                response["failed_tasks"] = getattr(result, 'failed_tasks', [])
            else:
                response["affected_dates"] = getattr(result, 'affected_dates', [])
                response["capacity_impact"] = getattr(result, 'capacity_changes', {})
            
            # Log plan-level decision to semantic memory
            if self.semantic_memory:
                plan_context = {
                    "plan_name": plan_name,
                    "plan_description": plan_description,
                    "tasks_count": len(tasks),
                    "success": result.success,
                    "task_categories": [task.get('category', 'general') for task in tasks],
                    "total_duration_hours": sum(
                        (datetime.fromisoformat(task['end_datetime'].replace('Z', '+00:00')) - 
                         datetime.fromisoformat(task['start_datetime'].replace('Z', '+00:00'))).total_seconds() / 3600
                        for task in tasks
                    ),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.semantic_memory.log_ai_decision(
                    decision_context=plan_context,
                    reasoning=f"Applied plan '{plan_name}' with {len(tasks)} tasks",
                    alternatives_considered=[]
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"ApplyPlanTool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


# === TOOL FACTORY ===

def create_langgraph_tools(world_updater: WorldUpdater, semantic_memory: Optional[SemanticMemory] = None, logger: Optional[logging.Logger] = None) -> List[BaseTool]:
    """
    Factory function to create all LangGraph tools for the planning system.
    
    Args:
        world_updater: WorldUpdater instance to execute operations
        semantic_memory: Optional semantic memory for learning and observability
        logger: Optional logger for tool operations
        
    Returns:
        List of configured LangGraph tools
    """
    tools = [
        AddTaskTool(world_updater, semantic_memory, logger),
        RemoveTaskTool(world_updater, semantic_memory, logger),
        ApplyPlanTool(world_updater, semantic_memory, logger)
    ]
    
    if logger:
        logger.info(f"Created {len(tools)} LangGraph tools with observability")
    
    return tools


# === USAGE EXAMPLE ===

def setup_planning_tools(world_updater: WorldUpdater, user_id: int, logger: Optional[logging.Logger] = None) -> List[BaseTool]:
    """
    Complete setup example for planning tools with semantic memory.
    
    Args:
        world_updater: Configured WorldUpdater instance
        user_id: User ID for semantic memory
        logger: Optional logger
        
    Returns:
        List of ready-to-use LangGraph tools
    """
    # Create semantic memory for learning
    semantic_memory = SemanticMemory(user_id=user_id, logger=logger)
    
    # Create tools with full observability
    tools = create_langgraph_tools(
        world_updater=world_updater,
        semantic_memory=semantic_memory, 
        logger=logger
    )
    
    if logger:
        logger.info(f"Planning system ready with {len(tools)} tools and semantic memory for user {user_id}")
    
    return tools
