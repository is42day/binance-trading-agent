"""Add trading decision journal table

Revision ID: 005_add_decision_journal
Revises: 004_add_exchange_order_ledger
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_decision_journal"
down_revision: Union[str, None] = "004_add_exchange_order_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trading_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("signal", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("blocked_reason", sa.String(), nullable=True),
        sa.Column("risk_approved", sa.String(), nullable=False, server_default="false"),
        sa.Column("execution_policy", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trading_decisions_symbol", "trading_decisions", ["symbol"])
    op.create_index("ix_trading_decisions_timestamp", "trading_decisions", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_trading_decisions_timestamp", table_name="trading_decisions")
    op.drop_index("ix_trading_decisions_symbol", table_name="trading_decisions")
    op.drop_table("trading_decisions")
