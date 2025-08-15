# app/cognitive/world/models.py
"""
SQLAlchemy ORM models for World State persistence
"""

from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Text, Float
from sqlalchemy.ext.declarative import declarative_base

from .state import CalendarizedTask

Base = declarative_base()


class CalendarizedTaskORM(Base):
    """
    SQLAlchemy ORM model for CalendarizedTask
    Maps the Pydantic model to database persistence
    """
    __tablename__ = "calendarized_tasks"
    
    # Primary identifiers
    task_id = Column(String, primary_key=True)
    goal_id = Column(String, nullable=False, index=True)
    plan_id = Column(String, nullable=False, index=True)
    
    # Task metadata
    title = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=False, index=True)
    estimated_minutes = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="scheduled")  # scheduled, in_progress, completed, cancelled, overdue
    
    # Optional relationships
    cycle_id = Column(String, nullable=True)
    occurrence_id = Column(String, nullable=True)
    
    # Metadata
    priority = Column(Integer, nullable=True)  # 1-5 scale
    tags = Column(Text, nullable=True)  # JSON string of tags list
    notes = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_pydantic(self) -> CalendarizedTask:
        """Convert ORM model to Pydantic model"""
        import json
        
        tags_list = []
        tags_value = getattr(self, 'tags', None)
        if tags_value:
            try:
                tags_list = json.loads(tags_value)
            except json.JSONDecodeError:
                tags_list = []
        
        return CalendarizedTask(
            task_id=getattr(self, 'task_id'),
            goal_id=getattr(self, 'goal_id'),
            plan_id=getattr(self, 'plan_id'),
            title=getattr(self, 'title'),
            start_datetime=getattr(self, 'start_datetime'),
            end_datetime=getattr(self, 'end_datetime'),
            estimated_minutes=getattr(self, 'estimated_minutes'),
            status=getattr(self, 'status'),
            cycle_id=getattr(self, 'cycle_id', None),
            occurrence_id=getattr(self, 'occurrence_id', None),
            priority=getattr(self, 'priority', None),
            tags=tags_list,
            notes=getattr(self, 'notes', None)
        )
    
    @classmethod
    def from_pydantic(cls, task: CalendarizedTask) -> "CalendarizedTaskORM":
        """Create ORM model from Pydantic model"""
        import json
        
        tags_json = None
        if task.tags:
            tags_json = json.dumps(task.tags)
        
        return cls(
            task_id=task.task_id,
            goal_id=task.goal_id,
            plan_id=task.plan_id,
            title=task.title,
            start_datetime=task.start_datetime,
            end_datetime=task.end_datetime,
            estimated_minutes=task.estimated_minutes,
            status=task.status,
            cycle_id=task.cycle_id,
            occurrence_id=task.occurrence_id,
            priority=task.priority,
            tags=tags_json,
            notes=task.notes
        )


class CapacityLoadORM(Base):
    """
    Track daily and weekly capacity loads
    Separate table for better performance and historical tracking
    """
    __tablename__ = "capacity_loads"
    
    id = Column(String, primary_key=True)  # user_id:date or user_id:week
    user_id = Column(String, nullable=False, index=True)
    period_type = Column(String, nullable=False)  # "daily" or "weekly"
    period_key = Column(String, nullable=False, index=True)  # "2025-08-16" or "2025-W33"
    load_hours = Column(Float, nullable=False, default=0.0)
    
    # Audit
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorldStateSnapshot(Base):
    """
    Optional: Store complete world state snapshots for debugging/rollback
    """
    __tablename__ = "world_state_snapshots"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    snapshot_data = Column(Text, nullable=False)  # JSON of complete world state
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(String, nullable=True)  # "pre_plan_application", "rollback_point", etc.
