"""Phase 4 CORRECTIVE: Aggressive cleanup + PlanNode canonical + ScheduledTask v2

Revision ID: 989b0456e09e
Revises: ccece8e57357
Create Date: 2025-10-24 16:34:54.393851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '989b0456e09e'
down_revision: Union[str, Sequence[str], None] = 'ccece8e57357'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 4 CORRECTIVE Migration: Aggressive cleanup + PlanNode canonical + ScheduledTask v2
    
    This migration transforms the existing schema to the Phase 4 target state:
    1. Drop legacy tables (habit_cycles, goal_occurrences, tasks)
    2. Create new plan_nodes table with UUID PKs and JSONB fields
    3. Replace scheduled_tasks with v2 schema (plan_node_id FK, UUID PK, enhanced fields)
    4. Add all required indices and constraints
    5. Create triggers for updated_at automation
    """
    
    # Import additional types
    from sqlalchemy.dialects import postgresql
    
    # ===== STEP 1: Drop foreign key constraints that reference legacy tables =====
    print("Dropping foreign key constraints to legacy tables...")
    
    # Drop constraints from scheduled_tasks to legacy tables
    try:
        op.drop_constraint('scheduled_tasks_cycle_id_fkey', 'scheduled_tasks', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
    
    try:
        op.drop_constraint('scheduled_tasks_task_id_fkey', 'scheduled_tasks', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
        
    try:
        op.drop_constraint('scheduled_tasks_occurrence_id_fkey', 'scheduled_tasks', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
    
    # Drop constraints from tasks to other legacy tables
    try:
        op.drop_constraint('tasks_cycle_id_fkey', 'tasks', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
        
    try:
        op.drop_constraint('tasks_occurrence_id_fkey', 'tasks', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
    
    # Drop constraints from goal_occurrences to habit_cycles
    try:
        op.drop_constraint('goal_occurrences_cycle_id_fkey', 'goal_occurrences', type_='foreignkey')
    except Exception:
        pass  # Constraint may not exist
    
    # ===== STEP 2: Drop legacy tables (aggressive cleanup) =====
    print("Dropping legacy tables...")
    op.drop_table('habit_cycles')
    op.drop_table('goal_occurrences') 
    op.drop_table('tasks')
    
    # ===== STEP 3: Create plan_nodes table =====
    print("Creating plan_nodes table...")
    op.create_table('plan_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('recurrence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dependencies', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0'),
        sa.Column('origin', sa.String(length=50), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('node_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('level >= 1', name='ck_plan_nodes_level_positive'),
        sa.CheckConstraint('progress >= 0.0 AND progress <= 1.0', name='ck_plan_nodes_progress_range'),
        sa.ForeignKeyConstraint(['parent_id'], ['plan_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ===== STEP 4: Drop and recreate scheduled_tasks with v2 schema =====
    print("Replacing scheduled_tasks with v2 schema...")
    op.drop_table('scheduled_tasks')
    
    op.create_table('scheduled_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('plan_node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('start_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_minutes', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_node_id'], ['plan_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ===== STEP 5: Create indices for performance =====
    print("Creating indices...")
    
    # plan_nodes indices
    op.create_index('ix_plan_nodes_plan_id', 'plan_nodes', ['plan_id'])
    op.create_index('ix_plan_nodes_parent_id', 'plan_nodes', ['parent_id'])
    op.create_index('ix_plan_nodes_status', 'plan_nodes', ['status'])
    op.create_index('plan_nodes_gin_tags', 'plan_nodes', ['tags'], postgresql_using='gin')
    op.create_index('plan_nodes_gin_node_metadata', 'plan_nodes', ['node_metadata'], postgresql_using='gin')
    op.create_index('plan_nodes_parent_child', 'plan_nodes', ['plan_id', 'parent_id'])
    
    # Unique constraint: one root node per plan
    op.create_index('plan_nodes_unique_root', 'plan_nodes', ['plan_id'], 
                    unique=True, postgresql_where=sa.text('parent_id IS NULL'))
    
    # scheduled_tasks indices
    op.create_index('ix_scheduled_tasks_plan_id', 'scheduled_tasks', ['plan_id'])
    op.create_index('ix_scheduled_tasks_plan_node_id', 'scheduled_tasks', ['plan_node_id'])
    op.create_index('ix_scheduled_tasks_user_id', 'scheduled_tasks', ['user_id'])
    op.create_index('ix_scheduled_tasks_goal_id', 'scheduled_tasks', ['goal_id'])
    op.create_index('ix_scheduled_tasks_start_datetime', 'scheduled_tasks', ['start_datetime'])
    op.create_index('scheduled_tasks_gin_tags', 'scheduled_tasks', ['tags'], postgresql_using='gin')
    
    # ===== STEP 6: Create triggers for updated_at automation =====
    print("Creating triggers...")
    
    # Create the trigger function (if it doesn't exist)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
           NEW.updated_at = now(); 
           RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for both tables
    op.execute("""
        CREATE TRIGGER update_plan_nodes_updated_at 
        BEFORE UPDATE ON plan_nodes 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_scheduled_tasks_updated_at 
        BEFORE UPDATE ON scheduled_tasks 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    print("Phase 4 migration completed successfully!")


def downgrade() -> None:
    """
    Downgrade from Phase 4 back to pre-Phase 4 state.
    
    This recreates the original schema structure.
    """
    
    print("Downgrading Phase 4 changes...")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_scheduled_tasks_updated_at ON scheduled_tasks")
    op.execute("DROP TRIGGER IF EXISTS update_plan_nodes_updated_at ON plan_nodes")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop new tables
    op.drop_table('scheduled_tasks')
    op.drop_table('plan_nodes')
    
    # Recreate original scheduled_tasks table (simplified version)
    op.create_table('scheduled_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=True),
        sa.Column('occurrence_id', sa.Integer(), nullable=True),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('scheduling_reason', sa.String(), nullable=True),
        sa.Column('scheduling_algorithm', sa.String(), nullable=True),
        sa.Column('scheduling_confidence', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('source_plan_version', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate legacy tables (empty structures)
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('habit_cycles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('goal_occurrences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    print("Downgrade completed - restored pre-Phase 4 schema")
