"""add_telegram_fields_to_user

Revision ID: a15b4918cbeb
Revises: d477e45f5ba2
Create Date: 2025-08-02 23:04:29.680753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a15b4918cbeb'
down_revision: Union[str, Sequence[str], None] = 'd477e45f5ba2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add Telegram-related fields to users table
    op.add_column('users', sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, unique=True))
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    
    # Create index on telegram_user_id for faster lookups
    op.create_index('ix_users_telegram_user_id', 'users', ['telegram_user_id'])
    
    # Make email field nullable since Telegram users don't need email
    op.alter_column('users', 'email', nullable=True)
    op.alter_column('users', 'hashed_password', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the index
    op.drop_index('ix_users_telegram_user_id', table_name='users')
    
    # Remove Telegram fields
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name') 
    op.drop_column('users', 'username')
    op.drop_column('users', 'telegram_user_id')
    
    # Revert email and password to non-nullable
    op.alter_column('users', 'email', nullable=False)
    op.alter_column('users', 'hashed_password', nullable=False)
