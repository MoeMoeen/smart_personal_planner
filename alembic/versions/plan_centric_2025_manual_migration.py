"""Plan-centric architecture migration
Revision ID: plan_centric_2025
Revises: a15b4918cbeb
Create Date: 2025-08-07 10:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'plan_centric_2025'
down_revision: Union[str, Sequence[str], None] = 'a15b4918cbeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Migrate to Plan-centric architecture - move execution logic from Goals to Plans"""
    
    # STEP 1: Add new columns to Plans table (execution logic)
    print("🔄 Adding execution logic columns to Plans table...")
    op.add_column('plans', sa.Column('goal_type', sa.Enum('project', 'habit', 'hybrid', name='goaltype'), nullable=True))
    op.add_column('plans', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('plans', sa.Column('end_date', sa.Date(), nullable=True))
    op.add_column('plans', sa.Column('progress', sa.Integer(), default=0, nullable=True))
    op.add_column('plans', sa.Column('recurrence_cycle', sa.String(), nullable=True))
    op.add_column('plans', sa.Column('goal_frequency_per_cycle', sa.Integer(), nullable=True))
    op.add_column('plans', sa.Column('goal_recurrence_count', sa.Integer(), nullable=True))
    op.add_column('plans', sa.Column('default_estimated_time_per_cycle', sa.Integer(), nullable=True))
    op.add_column('plans', sa.Column('source', sa.String(), default='AI', nullable=True))
    op.add_column('plans', sa.Column('ai_version', sa.String(), nullable=True))
    
    # STEP 2: Add timestamps to Goals table (lightweight metadata)
    print("🔄 Adding timestamps to Goals table...")
    op.add_column('goals', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('goals', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # STEP 3: Migrate data if any exists (move goal fields to related plans)
    print("🔄 Migrating existing data...")
    op.execute("""
        UPDATE plans SET 
            goal_type = goals.goal_type,
            start_date = goals.start_date,
            progress = COALESCE(goals.progress, 0),
            source = 'MIGRATED'
        FROM goals 
        WHERE plans.goal_id = goals.id 
        AND goals.goal_type IS NOT NULL
    """)
    
    # STEP 4: Update habit_cycles to reference goals instead of habit_goals
    print("🔄 Updating habit_cycles references...")
    op.add_column('habit_cycles', sa.Column('goal_id', sa.Integer(), nullable=True))
    
    # Migrate habit_cycles data if any exists
    op.execute("""
        UPDATE habit_cycles SET goal_id = habit_goals.id 
        FROM habit_goals 
        WHERE habit_cycles.habit_id = habit_goals.id
    """)
    
    # STEP 5: Remove old foreign key constraints
    print("🔄 Removing old constraints...")
    try:
        op.drop_constraint('habit_cycles_habit_id_fkey', 'habit_cycles', type_='foreignkey')
    except:
        pass  # Constraint might not exist
    
    # STEP 6: Drop old tables (careful order)
    print("🔄 Dropping old goal subtype tables...")
    try:
        op.drop_table('habit_goals')
    except:
        pass  # Table might not exist
        
    try:
        op.drop_table('project_goals')
    except:
        pass  # Table might not exist
    
    # STEP 7: Remove execution logic columns from Goals (make it lightweight)
    print("🔄 Making Goals table lightweight...")
    try:
        op.drop_column('goals', 'progress')
    except:
        pass
        
    try:
        op.drop_column('goals', 'goal_type')
    except:
        pass
        
    try:
        op.drop_column('goals', 'start_date')
    except:
        pass
    
    # STEP 8: Add new foreign key constraints
    print("🔄 Adding new constraints...")
    op.create_foreign_key('habit_cycles_goal_id_fkey', 'habit_cycles', 'goals', ['goal_id'], ['id'])
    
    # STEP 9: Clean up habit_cycles
    op.drop_column('habit_cycles', 'habit_id')
    
    # STEP 10: Make required fields NOT NULL after data migration
    print("🔄 Setting constraints on migrated data...")
    op.execute("UPDATE plans SET goal_type = 'project' WHERE goal_type IS NULL")
    op.execute("UPDATE plans SET start_date = CURRENT_DATE WHERE start_date IS NULL")
    op.execute("UPDATE plans SET end_date = CURRENT_DATE + INTERVAL '30 days' WHERE end_date IS NULL")
    op.execute("UPDATE plans SET source = 'AI' WHERE source IS NULL")
    
    # Now make them NOT NULL
    op.alter_column('plans', 'goal_type', nullable=False)
    op.alter_column('plans', 'start_date', nullable=False)
    op.alter_column('plans', 'end_date', nullable=False)
    op.alter_column('plans', 'source', nullable=False)
    
    # STEP 11: Update other constraints
    print("🔄 Updating other table constraints...")
    op.alter_column('goal_occurrences', 'plan_id', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('tasks', 'plan_id', existing_type=sa.INTEGER(), nullable=False)
    
    # STEP 12: Fix telegram user ID index
    print("🔄 Fixing telegram user index...")
    try:
        op.drop_constraint('users_telegram_user_id_key', 'users', type_='unique')
    except:
        pass
    try:
        op.drop_index('ix_users_telegram_user_id', table_name='users')
    except:
        pass
    op.create_index('ix_users_telegram_user_id', 'users', ['telegram_user_id'], unique=True)
    
    print("✅ Plan-centric architecture migration completed!")

def downgrade() -> None:
    """This is a complex structural change - downgrade not implemented"""
    raise NotImplementedError("Plan-centric architecture migration cannot be automatically downgraded")
