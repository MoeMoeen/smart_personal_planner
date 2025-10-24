"""Phase 4 HOTFIX: Add status column to scheduled_tasks

Revision ID: 038a9bb842fd
Revises: 989b0456e09e
Create Date: 2025-10-24 16:41:06.004239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '038a9bb842fd'
down_revision: Union[str, Sequence[str], None] = '989b0456e09e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing status column to scheduled_tasks table."""
    
    # First create the enum type if it doesn't exist (use CREATE TYPE IF NOT EXISTS for PostgreSQL 9.1+)
    op.execute("DO $$ BEGIN CREATE TYPE scheduledtaskstatus AS ENUM ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Add the status column
    op.add_column('scheduled_tasks', sa.Column('status', sa.Enum('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='scheduledtaskstatus'), nullable=False, server_default='SCHEDULED'))


def downgrade() -> None:
    """Remove status column from scheduled_tasks table."""
    op.drop_column('scheduled_tasks', 'status')
    op.execute("DROP TYPE IF EXISTS scheduledtaskstatus")
