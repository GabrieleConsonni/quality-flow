"""2026031410_QSM_035

Revision ID: b2c3d4e5f6a
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "b2c3d4e5f6a"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"

ENTITY_TABLES = (
    "json_payloads",
    "operations",
    "test_suites",
    "mock_servers",
    "mock_server_apis",
    "mock_server_queues",
    "ms_api_operations",
    "ms_queue_operations",
    "suite_items",
    "suite_item_operations",
)

EXECUTION_TABLES = (
    "suite_item_operation_executions",
    "suite_item_executions",
    "test_suite_executions",
    "mock_server_invocations",
    "step_operation_executions",
    "scenario_step_executions",
    "scenario_executions",
    "suite_test_executions",
    "suite_executions",
)


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    bind = op.get_bind()
    columns = inspect(bind).get_columns(table_name, schema=SCHEMA)
    return any(str(column.get("name") or "") == column_name for column in columns)


def _truncate_table_if_exists(table_name: str) -> None:
    if not _has_table(table_name):
        return
    op.execute(
        sa.text(
            f'TRUNCATE TABLE "{SCHEMA}"."{table_name}" RESTART IDENTITY CASCADE'
        )
    )


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name, schema=SCHEMA)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, str(column.name or "")):
        op.add_column(table_name, column, schema=SCHEMA)


def upgrade() -> None:
    for table_name in EXECUTION_TABLES:
        _truncate_table_if_exists(table_name)

    for table_name in ENTITY_TABLES:
        _drop_column_if_exists(table_name, "code")

    _drop_column_if_exists("test_suite_executions", "test_suite_code")
    _drop_column_if_exists("test_suite_executions", "requested_test_code")
    _drop_column_if_exists("suite_item_executions", "item_code")
    _drop_column_if_exists("suite_item_operation_executions", "operation_code")
    _drop_column_if_exists("mock_server_invocations", "mock_server_code")
    _drop_column_if_exists("mock_server_invocations", "trigger_code")
    _drop_column_if_exists("scenario_executions", "scenario_code")
    _drop_column_if_exists("scenario_executions", "requested_step_code")
    _drop_column_if_exists("scenario_step_executions", "step_code")
    _drop_column_if_exists("step_operation_executions", "operation_code")
    _drop_column_if_exists("suite_executions", "suite_code")
    _drop_column_if_exists("suite_executions", "requested_test_code")
    _drop_column_if_exists("suite_test_executions", "test_code")


def downgrade() -> None:
    for table_name in ENTITY_TABLES:
        _add_column_if_missing(
            table_name,
            sa.Column("code", sa.Text(), nullable=False, server_default=""),
        )

    _add_column_if_missing(
        "test_suite_executions",
        sa.Column("test_suite_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "test_suite_executions",
        sa.Column("requested_test_code", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "suite_item_executions",
        sa.Column("item_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "suite_item_operation_executions",
        sa.Column("operation_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "mock_server_invocations",
        sa.Column("mock_server_code", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "mock_server_invocations",
        sa.Column("trigger_code", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "scenario_executions",
        sa.Column("scenario_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "scenario_executions",
        sa.Column("requested_step_code", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "scenario_step_executions",
        sa.Column("step_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "step_operation_executions",
        sa.Column("operation_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "suite_executions",
        sa.Column("suite_code", sa.Text(), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "suite_executions",
        sa.Column("requested_test_code", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "suite_test_executions",
        sa.Column("test_code", sa.Text(), nullable=False, server_default=""),
    )
