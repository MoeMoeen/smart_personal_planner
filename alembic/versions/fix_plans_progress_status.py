"""Fix Plans Progress Status Column

Revision ID: fix_plans_progress_status
Revises: enhanced_models_clean
Create Date: 2025-08-15 12:45:00.000000

Adds missing progress_status column to plans table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'fix_plans_progress_status'
down_revision = 'enhanced_models_clean'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing progress_status column to plans table."""
    print("🔧 Adding missing progress_status column to plans...")
    
    # Add progress_status column to plans table
    op.add_column('plans',
        sa.Column('progress_status',
                 sa.Enum('not_started', 'in_progress', 'completed', 'blocked', 'on_hold', name='progressstatus'), 
                 nullable=False, server_default='not_started'))
    
    print("✅ Plans progress_status column added successfully!")


def downgrade():
    """Remove progress_status column from plans table."""
    print("⏪ Removing progress_status column from plans...")
    
    op.drop_column('plans', 'progress_status')
    
    print("✅ Plans progress_status column removed successfully!")
