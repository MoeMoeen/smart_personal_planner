"""Fix Task Model Column Names

Revision ID: fix_task_columns
Revises: fix_plans_progress_status
Create Date: 2025-08-15 13:00:00.000000

Fixes task column names to match the model expectations.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'fix_task_columns'
down_revision = 'fix_plans_progress_status'
branch_labels = None
depends_on = None


def upgrade():
    """Fix task column names and add missing columns."""
    print("🔧 Fixing task column names and adding missing columns...")
    
    # 1. Rename execution_status to status
    print("📝 Renaming execution_status to status...")
    op.alter_column('tasks', 'execution_status', new_column_name='status')
    
    # 2. Add missing completed_at column
    print("⏰ Adding completed_at column...")
    op.add_column('tasks',
        sa.Column('completed_at', sa.DateTime, nullable=True))
    
    # 3. Add missing blocked_reason column
    print("🚫 Adding blocked_reason column...")
    op.add_column('tasks',
        sa.Column('blocked_reason', sa.String, nullable=True))
    
    print("✅ Task columns fixed successfully!")


def downgrade():
    """Revert task column changes."""
    print("⏪ Reverting task column changes...")
    
    # Remove added columns
    op.drop_column('tasks', 'blocked_reason')
    op.drop_column('tasks', 'completed_at')
    
    # Rename status back to execution_status
    op.alter_column('tasks', 'status', new_column_name='execution_status')
    
    print("✅ Task column changes reverted successfully!")
