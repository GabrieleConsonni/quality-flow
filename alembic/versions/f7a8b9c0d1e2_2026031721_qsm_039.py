"""2026031721_QSM_039

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-17 21:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"
DEFINITIONS_TABLE = "command_constant_definitions"

IMPACTED_TABLES_DELETE_ORDER: tuple[str, ...] = (
    DEFINITIONS_TABLE,
    "suite_item_commands",
    "ms_api_commands",
    "ms_queue_commands",
    "test_suite_executions",
    "test_suite_schedules",
    "mock_server_invocations",
    "mock_server_apis",
    "mock_server_queues",
    "suite_items",
    "test_suites",
    "mock_servers",
)


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def _delete_all_rows(table_name: str) -> None:
    if not _has_table(table_name):
        return
    op.execute(sa.text(f'DELETE FROM "{SCHEMA}"."{table_name}"'))


def upgrade() -> None:
    if not _has_table(DEFINITIONS_TABLE):
        op.create_table(
            DEFINITIONS_TABLE,
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("owner_type", sa.Text(), nullable=False),
            sa.Column("suite_id", sa.Text(), nullable=True),
            sa.Column("suite_item_id", sa.Text(), nullable=True),
            sa.Column("mock_server_api_id", sa.Text(), nullable=True),
            sa.Column("mock_server_queue_id", sa.Text(), nullable=True),
            sa.Column("command_id", sa.Text(), nullable=False),
            sa.Column("command_order", sa.Numeric(), nullable=False),
            sa.Column("section_type", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("context_scope", sa.Text(), nullable=False),
            sa.Column("value_type", sa.Text(), nullable=False),
            sa.Column("declared_at_order", sa.Numeric(), nullable=False),
            sa.Column("deleted_at_order", sa.Numeric(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_quality_flow_command_constant_definitions_suite_id",
            DEFINITIONS_TABLE,
            ["suite_id"],
            unique=False,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_quality_flow_command_constant_definitions_mock_api_id",
            DEFINITIONS_TABLE,
            ["mock_server_api_id"],
            unique=False,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_quality_flow_command_constant_definitions_mock_queue_id",
            DEFINITIONS_TABLE,
            ["mock_server_queue_id"],
            unique=False,
            schema=SCHEMA,
        )

    for table_name in IMPACTED_TABLES_DELETE_ORDER:
        _delete_all_rows(table_name)


def downgrade() -> None:
    if not _has_table(DEFINITIONS_TABLE):
        return
    op.drop_index(
        "ix_quality_flow_command_constant_definitions_mock_queue_id",
        table_name=DEFINITIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_quality_flow_command_constant_definitions_mock_api_id",
        table_name=DEFINITIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_quality_flow_command_constant_definitions_suite_id",
        table_name=DEFINITIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(DEFINITIONS_TABLE, schema=SCHEMA)
