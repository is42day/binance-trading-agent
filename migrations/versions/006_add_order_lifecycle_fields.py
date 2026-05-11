"""Add last_booked_quantity and cancel_reason to exchange_orders.

Revision ID: 006
Revises: 005
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exchange_orders") as batch_op:
        batch_op.add_column(
            sa.Column("last_booked_quantity", sa.Float(), nullable=False, server_default="0.0")
        )
        batch_op.add_column(
            sa.Column("cancel_reason", sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("exchange_orders") as batch_op:
        batch_op.drop_column("cancel_reason")
        batch_op.drop_column("last_booked_quantity")
