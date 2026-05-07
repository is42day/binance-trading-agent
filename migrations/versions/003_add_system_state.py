"""Add system_state table for shared control flags

Revision ID: 003_add_system_state
Revises: 002_add_heartbeat
Create Date: 2026-05-07 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_add_system_state"
down_revision: Union[str, None] = "002_add_heartbeat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_state",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        comment="Shared system control state such as emergency stop flags.",
    )
    op.create_index("ix_system_state_updated_at", "system_state", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_system_state_updated_at", table_name="system_state")
    op.drop_table("system_state")
