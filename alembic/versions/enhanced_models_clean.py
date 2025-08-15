"""Enhanced Models Migration - Clean Version

Revision ID: enhanced_models_clean
Revises: 622e964db082
Create Date: 2025-08-15 12:30:00.000000

Adds enhanced enum fields and performance columns for production-ready planning system.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'enhanced_models_clean'
down_revision = '622e964db082'
branch_labels = None
depends_on = None


def upgrade():
    """Enhanced models migration - columns and enums only."""
    print("🚀 Starting Enhanced Models Migration...")
    
    # 1. Create enhanced enum types
    print("📝 Creating enhanced enum types...")
    
    # Task execution status enum
    op.execute("CREATE TYPE taskexecutionstatus AS ENUM ('todo', 'in_progress', 'completed', 'blocked', 'cancelled')")
    
    # Progress status enum  
    op.execute("CREATE TYPE progressstatus AS ENUM ('not_started', 'in_progress', 'completed', 'blocked', 'on_hold')")
    
    # Recurrence cycle enum
    op.execute("CREATE TYPE recurrencecycle AS ENUM ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', 'custom')")
    
    # Plan source enum
    op.execute("CREATE TYPE plansource AS ENUM ('ai_generated', 'user_created', 'template', 'imported', 'refined')")
    
    # 2. Add missing timestamp columns to tasks table
    print("⏰ Adding timestamp columns to tasks...")
    op.add_column('tasks',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('tasks', 
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # 3. Add missing enum columns to tasks table
    print("📊 Adding enhanced enum columns to tasks...")
    op.add_column('tasks',
        sa.Column('execution_status', 
                 sa.Enum('todo', 'in_progress', 'completed', 'blocked', 'cancelled', name='taskexecutionstatus'),
                 nullable=False, server_default='todo'))
    
    op.add_column('tasks',
        sa.Column('progress_status',
                 sa.Enum('not_started', 'in_progress', 'completed', 'blocked', 'on_hold', name='progressstatus'), 
                 nullable=False, server_default='not_started'))
    
    op.add_column('tasks',
        sa.Column('recurrence_cycle',
                 sa.Enum('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', 'custom', name='recurrencecycle'),
                 nullable=True))
    
    # 4. Add missing date column to tasks table
    print("📅 Adding date columns to tasks...")
    op.add_column('tasks',
        sa.Column('start_date', sa.Date, nullable=True))
    
    # 5. Add enhanced enum columns to plans table
    print("📋 Adding enhanced enum columns to plans...")
    op.add_column('plans',
        sa.Column('plan_source',
                 sa.Enum('ai_generated', 'user_created', 'template', 'imported', 'refined', name='plansource'),
                 nullable=False, server_default='user_created'))
    
    # 6. Add JSON metadata fields
    print("🔧 Adding JSON fields for enhanced functionality...")
    
    # Add execution_metadata JSON field to tasks table
    op.add_column('tasks',
        sa.Column('execution_metadata', sa.JSON, nullable=True))
    
    # Add plan_metadata JSON field to plans table
    op.add_column('plans',
        sa.Column('plan_metadata', sa.JSON, nullable=True))
    
    print("✅ Enhanced Models Migration completed successfully!")


def downgrade():
    """Rollback enhanced models migration"""
    
    print("⏪ Rolling back Enhanced Models Migration...")
    
    # 1. Drop JSON columns
    print("🗑️ Dropping JSON columns...")
    
    op.drop_column('plans', 'plan_metadata')
    op.drop_column('tasks', 'execution_metadata')
    
    # 2. Drop enhanced enum columns
    print("🗑️ Dropping enhanced enum columns...")
    
    op.drop_column('plans', 'plan_source')
    op.drop_column('tasks', 'start_date')
    op.drop_column('tasks', 'recurrence_cycle')
    op.drop_column('tasks', 'progress_status')
    op.drop_column('tasks', 'execution_status')
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'created_at')
    
    # 3. Drop enum types
    print("🗑️ Dropping enum types...")
    
    op.execute('DROP TYPE IF EXISTS plansource')
    op.execute('DROP TYPE IF EXISTS recurrencecycle') 
    op.execute('DROP TYPE IF EXISTS progressstatus')
    op.execute('DROP TYPE IF EXISTS taskexecutionstatus')
    
    print("✅ Enhanced Models Migration rollback completed!")
