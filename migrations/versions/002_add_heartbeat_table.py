"""Add heartbeat table for agent liveness monitoring

Revision ID: 002_add_heartbeat
Revises: 001_initial_orm
Create Date: 2025-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_heartbeat'
down_revision: Union[str, None] = '001_initial_orm'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create heartbeat table for agent liveness monitoring
    op.create_table('heartbeat',
        sa.Column('service_name', sa.String(), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='healthy'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('service_name'),
        comment='Heartbeat records for monitoring service liveness. Each service updates its row every N seconds.'
    )
    
    # Create index on last_update for staleness queries (e.g., find heartbeats older than N seconds)
    op.create_index('ix_heartbeat_last_update', 'heartbeat', ['last_update'], unique=False)
    
    # Create index on status for querying unhealthy services
    op.create_index('ix_heartbeat_status', 'heartbeat', ['status'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_heartbeat_status', table_name='heartbeat')
    op.drop_index('ix_heartbeat_last_update', table_name='heartbeat')
    
    # Drop table
    op.drop_table('heartbeat')
