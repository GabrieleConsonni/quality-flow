"""2026031612_QSM_036

Revision ID: f1e2d3c4b5a6
Revises: c4d5e6f7a8b9
Create Date: 2026-03-16 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name, schema=SCHEMA))


def _rename_table_if_exists(old_name: str, new_name: str):
    if _has_table(old_name) and not _has_table(new_name):
        op.rename_table(old_name, new_name, schema=SCHEMA)


def upgrade() -> None:
    _rename_table_if_exists("suite_item_operations", "suite_item_commands")
    _rename_table_if_exists("suite_item_operation_executions", "suite_item_command_executions")
    _rename_table_if_exists("ms_api_operations", "ms_api_commands")
    _rename_table_if_exists("ms_queue_operations", "ms_queue_commands")

    if _has_table("suite_item_commands"):
        with op.batch_alter_table("suite_item_commands", schema=SCHEMA) as batch_op:
            if _has_column("suite_item_commands", "operation_type"):
                batch_op.alter_column("operation_type", new_column_name="command_code")
            if not _has_column("suite_item_commands", "command_type"):
                batch_op.add_column(sa.Column("command_type", sa.Text(), nullable=True))

    if _has_table("ms_api_commands"):
        with op.batch_alter_table("ms_api_commands", schema=SCHEMA) as batch_op:
            if _has_column("ms_api_commands", "operation_type"):
                batch_op.alter_column("operation_type", new_column_name="command_code")
            if not _has_column("ms_api_commands", "command_type"):
                batch_op.add_column(sa.Column("command_type", sa.Text(), nullable=True))

    if _has_table("ms_queue_commands"):
        with op.batch_alter_table("ms_queue_commands", schema=SCHEMA) as batch_op:
            if _has_column("ms_queue_commands", "operation_type"):
                batch_op.alter_column("operation_type", new_column_name="command_code")
            if not _has_column("ms_queue_commands", "command_type"):
                batch_op.add_column(sa.Column("command_type", sa.Text(), nullable=True))

    if _has_table("suite_item_command_executions"):
        with op.batch_alter_table("suite_item_command_executions", schema=SCHEMA) as batch_op:
            if _has_column("suite_item_command_executions", "suite_item_operation_id"):
                batch_op.alter_column("suite_item_operation_id", new_column_name="suite_item_command_id")
            if _has_column("suite_item_command_executions", "operation_description"):
                batch_op.alter_column("operation_description", new_column_name="command_description")
            if _has_column("suite_item_command_executions", "operation_order"):
                batch_op.alter_column("operation_order", new_column_name="command_order")

    bind = op.get_bind()
    for table_name in ("suite_item_commands", "ms_api_commands", "ms_queue_commands"):
        if _has_table(table_name) and _has_column(table_name, "command_type"):
            bind.execute(
                text(
                    f"""
                    UPDATE {SCHEMA}.{table_name}
                    SET command_type = CASE
                        WHEN command_code IN ('initConstant', 'deleteConstant', 'data', 'data-from-json-array', 'data-from-db', 'data-from-queue', 'set-var') THEN 'context'
                        WHEN command_code IN ('jsonEquals', 'jsonEmpty', 'jsonNotEmpty', 'jsonContains', 'jsonArrayEquals', 'jsonArrayEmpty', 'jsonArrayNotEmpty', 'jsonArrayContains', 'assert') THEN 'assert'
                        ELSE 'action'
                    END
                    WHERE command_type IS NULL
                    """
                )
            )
            with op.batch_alter_table(table_name, schema=SCHEMA) as batch_op:
                batch_op.alter_column("command_type", nullable=False)


def downgrade() -> None:
    if _has_table("suite_item_command_executions"):
        with op.batch_alter_table("suite_item_command_executions", schema=SCHEMA) as batch_op:
            if _has_column("suite_item_command_executions", "suite_item_command_id"):
                batch_op.alter_column("suite_item_command_id", new_column_name="suite_item_operation_id")
            if _has_column("suite_item_command_executions", "command_description"):
                batch_op.alter_column("command_description", new_column_name="operation_description")
            if _has_column("suite_item_command_executions", "command_order"):
                batch_op.alter_column("command_order", new_column_name="operation_order")

    for table_name in ("suite_item_commands", "ms_api_commands", "ms_queue_commands"):
        if _has_table(table_name):
            with op.batch_alter_table(table_name, schema=SCHEMA) as batch_op:
                if _has_column(table_name, "command_type"):
                    batch_op.drop_column("command_type")
                if _has_column(table_name, "command_code"):
                    batch_op.alter_column("command_code", new_column_name="operation_type")

    _rename_table_if_exists("suite_item_commands", "suite_item_operations")
    _rename_table_if_exists("suite_item_command_executions", "suite_item_operation_executions")
    _rename_table_if_exists("ms_api_commands", "ms_api_operations")
    _rename_table_if_exists("ms_queue_commands", "ms_queue_operations")
