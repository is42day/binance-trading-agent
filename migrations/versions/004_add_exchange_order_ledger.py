"""Add exchange order ledger

Revision ID: 004_add_exchange_order_ledger
Revises: 003_add_system_state
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "004_add_exchange_order_ledger"
down_revision: Union[str, None] = "003_add_system_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trades", sa.Column("client_order_id", sa.String(), nullable=True))
    op.create_index(
        "ix_trades_client_order_id",
        "trades",
        ["client_order_id"],
        unique=True,
    )

    op.create_table(
        "exchange_orders",
        sa.Column("client_order_id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("order_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("executed_quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("avg_fill_price", sa.Float(), nullable=True),
        sa.Column("fee", sa.Float(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("client_order_id"),
    )
    op.create_index("ix_exchange_orders_order_id", "exchange_orders", ["order_id"], unique=False)
    op.create_index("ix_exchange_orders_symbol", "exchange_orders", ["symbol"], unique=False)
    op.create_index("ix_exchange_orders_status", "exchange_orders", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exchange_orders_status", table_name="exchange_orders")
    op.drop_index("ix_exchange_orders_symbol", table_name="exchange_orders")
    op.drop_index("ix_exchange_orders_order_id", table_name="exchange_orders")
    op.drop_table("exchange_orders")

    op.drop_index("ix_trades_client_order_id", table_name="trades")
    op.drop_column("trades", "client_order_id")
