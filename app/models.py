# app/models.py - Phase 4: Aggressive cleanup with v1.2/v1.3 alignment

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    Date,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
    text
)
from sqlalchemy import Enum as SQLAlchemyEnum, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy.sql import func
from app.cognitive.contracts.types import MemoryObject

# ─────────────────────────────────────────────────────────────
# SQLAlchemy Base and Enums
# ─────────────────────────────────────────────────────────────

Base = declarative_base()


# Legacy enums to keep (minimal, stable interfaces)
class GoalType(str, enum.Enum):
    project = "project"
    habit = "habit"
    hybrid = "hybrid"


class PlanSource(str, enum.Enum):
    AI_GENERATED = "ai_generated"
    MANUAL_CREATED = "manual_created"
    IMPORTED = "imported"
    REFINED = "refined"
    TEMPLATE = "template"


class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"


class PlanFeedbackAction(str, enum.Enum):
    APPROVE = "approve"
    REQUEST_REFINEMENT = "request_refinement"


class ScheduledTaskStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


# ─────────────────────────────────────────────────────────────
# Core Models (KEPT with minimal changes)
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    
    # Telegram integration fields
    telegram_user_id = Column(BigInteger, unique=True, nullable=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (cleaned up - removed legacy references)
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="user", cascade="all, delete-orphan")
    capacity_snapshots = relationship("CapacitySnapshot", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (cleaned up - removed legacy references)
    user = relationship("User", back_populates="goals")
    plans = relationship("Plan", back_populates="goal", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="goal", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Goal(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)

    # Execution fields
    goal_type = Column(SQLAlchemyEnum(GoalType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    progress = Column(Integer, default=0)
    progress_status = Column(SQLAlchemyEnum(ProgressStatus), nullable=False, default=ProgressStatus.NOT_STARTED)

    # AI metadata fields
    source = Column(SQLAlchemyEnum(PlanSource), nullable=False, default=PlanSource.AI_GENERATED)
    ai_version = Column(String, nullable=True)
    refinement_round = Column(Integer, default=0, nullable=True)
    source_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Performance indexes
    __table_args__ = (
        Index('ix_plans_user_goal_type', 'user_id', 'goal_type'),
        Index('ix_plans_date_range', 'start_date', 'end_date'),
        Index('ix_plans_approval_status', 'is_approved', 'goal_type'),
        Index('ix_plans_progress_status', 'progress_status', 'goal_type'),
    )

    # Relationships (cleaned up - removed legacy references)
    goal = relationship("Goal", back_populates="plans")
    user = relationship("User", back_populates="plans")
    feedback = relationship("Feedback", back_populates="plan", cascade="all, delete-orphan", uselist=False)
    scheduled_tasks = relationship("ScheduledTask", back_populates="plan", cascade="all, delete-orphan")
    plan_nodes = relationship("PlanNode", back_populates="plan", cascade="all, delete-orphan")
    
    # Self-referential for refinements
    source_plan = relationship("Plan", remote_side=[id], back_populates="refined_plans", uselist=False)
    refined_plans = relationship("Plan", back_populates="source_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan(id={self.id}, goal_id={self.goal_id}, goal_type={self.goal_type}, is_approved={self.is_approved})>"


# ─────────────────────────────────────────────────────────────
# NEW: PlanNode Table (v1.2/v1.3 aligned)
# ─────────────────────────────────────────────────────────────

class PlanNode(Base):
    """
    Atomic structural unit for plan hierarchy - replaces legacy Task/HabitCycle/GoalOccurrence.
    Implements Phase 4 specs with UUID PKs, proper constraints, and cascade behavior.
    """
    __tablename__ = "plan_nodes"

    # Core identity (UUID as specified)
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(PostgresUUID(as_uuid=True), ForeignKey("plan_nodes.id", ondelete="CASCADE"), nullable=True, index=True)

    # Hierarchy and typing
    node_type = Column(String(20), nullable=False)  # goal/phase/cycle/sub_goal/task/sub_task/micro_goal
    level = Column(Integer, nullable=False, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    
    # Behavioral attributes
    recurrence = Column(String(20), nullable=True)  # none/daily/weekly/monthly/quarterly/yearly
    dependencies = Column(JSONB, nullable=False, default=text("'[]'::jsonb"))  # [{"node_id": "<uuid>", "type": "finish_to_start", "lag_lead_minutes": 0}]
    
    # Status and progress
    status = Column(String(20), nullable=False, default="pending")  # pending/in_progress/done/blocked
    progress = Column(Float, nullable=False, server_default=text("0.0"))  # 0.0-1.0
    
    # Metadata
    origin = Column(String(30), nullable=False, default="system")  # system/user_feedback/ai_adaptation
    order_index = Column(Integer, nullable=True)  # for sibling ordering
    tags = Column(JSONB, nullable=False, default=text("'[]'::jsonb"))
    # Use node_metadata to avoid SQLAlchemy reserved 'metadata' attribute clash
    node_metadata = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint('level >= 1', name='ck_plan_nodes_level_positive'),
        CheckConstraint('progress >= 0.0 AND progress <= 1.0', name='ck_plan_nodes_progress_0_1'),
        # Performance indices as specified
        Index('ix_plan_nodes_plan_id', 'plan_id'),
        Index('ix_plan_nodes_plan_node_type', 'plan_id', 'node_type'),
        Index('ix_plan_nodes_plan_level', 'plan_id', 'level'),
        Index('ix_plan_nodes_parent_order', 'parent_id', 'order_index'),
        # GIN indices for JSONB fields
        Index('ix_plan_nodes_tags_gin', 'tags', postgresql_using='gin'),
        Index('ix_plan_nodes_dependencies_gin', 'dependencies', postgresql_using='gin'),
        # One root (L1, no parent) per plan
        Index(
            'ux_plan_nodes_one_root_per_plan',
            'plan_id',
            unique=True,
            postgresql_where=text("level = 1 AND parent_id IS NULL")
        ),
    )

    # Relationships
    plan = relationship("Plan", back_populates="plan_nodes")
    
    # Self-referential hierarchy
    children = relationship(
        "PlanNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="[PlanNode.parent_id]",
    )
    parent = relationship(
        "PlanNode",
        back_populates="children",
        remote_side=[id],
    )
    
    # Link to scheduled tasks
    scheduled_tasks = relationship("ScheduledTask", back_populates="plan_node", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlanNode(id={self.id}, node_type={self.node_type}, level={self.level}, title='{self.title}')>"


# ─────────────────────────────────────────────────────────────
# UPDATED: ScheduledTask (enhanced with plan_node_id)
# ─────────────────────────────────────────────────────────────

class ScheduledTask(Base):
    """
    Enhanced scheduled task with UUID PK and plan_node_id FK.
    Maps 1:1 to Pydantic ScheduledBlock as specified.
    """
    __tablename__ = "scheduled_tasks"
    
    # UUID primary key as specified
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core FKs with CASCADE behavior
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_node_id = Column(PostgresUUID(as_uuid=True), ForeignKey("plan_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Context FKs
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Scheduling data (timezone-aware as specified)
    title = Column(String(255), nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    end_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    estimated_minutes = Column(Integer, nullable=True)
    
    # Metadata
    tags = Column(JSONB, nullable=False, default=text("'[]'::jsonb"))
    notes = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLAlchemyEnum(ScheduledTaskStatus), nullable=False, default=ScheduledTaskStatus.SCHEDULED)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint('estimated_minutes IS NULL OR estimated_minutes >= 0', name='ck_scheduled_tasks_est_minutes_positive'),
        CheckConstraint('end_datetime > start_datetime', name='ck_scheduled_tasks_time_valid'),
        # Performance indices as specified
        Index('ix_scheduled_tasks_plan_id', 'plan_id'),
        Index('ix_scheduled_tasks_plan_node_id', 'plan_node_id'),
        Index('ix_scheduled_tasks_user_datetime', 'user_id', 'start_datetime'),
        Index('ix_scheduled_tasks_plan_datetime', 'plan_id', 'start_datetime'),
        Index('ix_scheduled_tasks_status', 'status'),
        Index('ix_scheduled_tasks_goal_datetime', 'goal_id', 'start_datetime'),
        # GIN index for tags
        Index('ix_scheduled_tasks_tags_gin', 'tags', postgresql_using='gin'),
    )
    
    # Relationships
    user = relationship("User", back_populates="scheduled_tasks")
    goal = relationship("Goal", back_populates="scheduled_tasks")
    plan = relationship("Plan", back_populates="scheduled_tasks")
    plan_node = relationship("PlanNode", back_populates="scheduled_tasks")

    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, title='{self.title}', start={self.start_datetime}, status={self.status})>"


# ─────────────────────────────────────────────────────────────
# Feedback Model (minor cleanup)
# ─────────────────────────────────────────────────────────────

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, unique=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    
    feedback_text = Column(String, nullable=False)
    suggested_changes = Column(JSON, nullable=True)
    plan_feedback_action = Column(SQLAlchemyEnum(PlanFeedbackAction, name="PlanFeedbackAction"), nullable=False)
    feedback_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Performance indexes
    __table_args__ = (
        Index('ix_feedback_user_created', 'user_id', 'created_at'),
        Index('ix_feedback_plan_action', 'plan_id', 'plan_feedback_action'),
    )

    # Relationships
    goal = relationship("Goal", back_populates="feedback", uselist=False)
    user = relationship("User", back_populates="feedback")
    plan = relationship("Plan", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, action={self.plan_feedback_action})>"


# ─────────────────────────────────────────────────────────────
# Analytics and Memory Models (KEPT as-is)
# ─────────────────────────────────────────────────────────────

class CapacitySnapshot(Base):
    __tablename__ = "capacity_snapshots"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    period_type = Column(String, nullable=False)
    period_key = Column(String, nullable=False)
    
    limit_hours = Column(String, nullable=False)
    scheduled_hours = Column(String, nullable=False)
    actual_hours = Column(String, nullable=True)
    utilization_rate = Column(String, nullable=True)
    
    snapshot_datetime = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    user = relationship("User", back_populates="capacity_snapshots")
    
    def __repr__(self):
        return f"<CapacitySnapshot(user_id={self.user_id}, period={self.period_key}, scheduled={self.scheduled_hours}h/{self.limit_hours}h)>"


class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    goal_id = Column(Integer, nullable=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def orm_to_memory_object(self) -> MemoryObject:
        return MemoryObject(
            memory_id=str(self.id) if self.id is not None else None,
            user_id=str(self.user_id) if self.user_id is not None else "",
            goal_id=str(self.goal_id) if self.goal_id is not None else None,
            type="episodic",
            content=self.content if not isinstance(self.content, Column) else {},
            timestamp=self.created_at if isinstance(self.created_at, datetime) else datetime.now(timezone.utc),
        )


class SemanticMemory(Base):
    __tablename__ = "semantic_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def orm_to_memory_object(self) -> MemoryObject:
        return MemoryObject(
            memory_id=str(self.id) if self.id is not None else None,
            user_id=str(self.user_id) if self.user_id is not None else "",
            goal_id=None,
            type="semantic",
            content=self.content if not isinstance(self.content, Column) else {},
            timestamp=self.created_at if isinstance(self.created_at, datetime) else datetime.now(timezone.utc),
        )


class ProceduralMemory(Base):
    __tablename__ = "procedural_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def orm_to_memory_object(self) -> MemoryObject:
        return MemoryObject(
            memory_id=str(self.id) if self.id is not None else None,
            user_id=str(self.user_id) if self.user_id is not None else "",
            goal_id=None,
            type="procedural",
            content=self.content if not isinstance(self.content, Column) else {},
            timestamp=self.created_at if isinstance(self.created_at, datetime) else datetime.now(timezone.utc),
        )


# ─────────────────────────────────────────────────────────────
# Database Triggers for updated_at (PostgreSQL)
# ─────────────────────────────────────────────────────────────

# Note: These would be applied via Alembic migration, not in the ORM directly
# CREATE OR REPLACE FUNCTION update_updated_at_column()
# RETURNS TRIGGER AS $$
# BEGIN
#     NEW.updated_at = NOW();
#     RETURN NEW;
# END;
# $$ language 'plpgsql';
#
# CREATE TRIGGER update_plan_nodes_updated_at BEFORE UPDATE ON plan_nodes
#     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
#
# CREATE TRIGGER update_scheduled_tasks_updated_at BEFORE UPDATE ON scheduled_tasks
#     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();