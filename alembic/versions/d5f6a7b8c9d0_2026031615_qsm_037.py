"""2026031615_QSM_037

Revision ID: d5f6a7b8c9d0
Revises: f1e2d3c4b5a6
Create Date: 2026-03-16 15:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "d5f6a7b8c9d0"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"
TABLE_NAME = "test_suite_schedules"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def upgrade() -> None:
    if _has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("test_suite_id", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("frequency_unit", sa.Text(), nullable=False),
        sa.Column("frequency_value", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=True),
        sa.Column("end_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_status", sa.Text(), nullable=False, server_default=sa.text("'idle'")),
        sa.Column("last_execution_id", sa.Text(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["test_suite_id"], [f"{SCHEMA}.test_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_quality_flow_test_suite_schedules_suite_id",
        TABLE_NAME,
        ["test_suite_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_quality_flow_test_suite_schedules_next_run_at",
        TABLE_NAME,
        ["next_run_at"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    if not _has_table(TABLE_NAME):
        return
    op.drop_index("ix_quality_flow_test_suite_schedules_next_run_at", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_quality_flow_test_suite_schedules_suite_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
