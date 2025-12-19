"""Initial ORM migration - create positions and trades tables

Revision ID: 001_initial_orm
Revises:
Create Date: 2025-10-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_orm'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create positions table
    op.create_table('positions',
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('average_price', sa.Float(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('unrealized_pnl', sa.Float(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
    )
    
    # Create index on positions symbol (redundant with PK but explicit)
    op.create_index('ix_positions_symbol', 'positions', ['symbol'], unique=False)
    
    # Create trades table
    op.create_table('trades',
        sa.Column('trade_id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('trade_id'),
        sa.UniqueConstraint('order_id', name='uq_trades_order_id')  # Prevent duplicate orders
    )
    
    # Create indexes for common query patterns
    op.create_index('ix_trades_symbol', 'trades', ['symbol'], unique=False)
    op.create_index('ix_trades_timestamp', 'trades', ['timestamp'], unique=False)
    op.create_index('ix_trades_symbol_timestamp', 'trades', ['symbol', 'timestamp'], unique=False)
    op.create_index('ix_trades_correlation_id', 'trades', ['correlation_id'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_trades_correlation_id', table_name='trades')
    op.drop_index('ix_trades_symbol_timestamp', table_name='trades')
    op.drop_index('ix_trades_timestamp', table_name='trades')
    op.drop_index('ix_trades_symbol', table_name='trades')
    op.drop_index('ix_positions_symbol', table_name='positions')
    
    # Drop tables
    op.drop_table('trades')
    op.drop_table('positions')
