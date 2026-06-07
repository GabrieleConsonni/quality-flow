"""2026030912_QSM_034

Revision ID: a1b2c3d4e5f6
Revises: 9a8b7c6d5e4f
Create Date: 2026-03-09 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def _drop_table_if_exists(table_name: str) -> None:
    if _has_table(table_name):
        op.drop_table(table_name, schema=SCHEMA)


def upgrade() -> None:
    _drop_table_if_exists("step_operation_executions")
    _drop_table_if_exists("scenario_step_executions")
    _drop_table_if_exists("scenario_executions")
    _drop_table_if_exists("step_operations")
    _drop_table_if_exists("scenario_steps")
    _drop_table_if_exists("steps")
    _drop_table_if_exists("scenarios")

    op.create_table(
        "test_suites",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "suite_items",
        sa.Column("test_suite_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("hook_phase", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("on_failure", sa.Text(), nullable=False, server_default="ABORT"),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_suite_id"],
            [f"{SCHEMA}.test_suites.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "suite_item_operations",
        sa.Column("suite_item_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["suite_item_id"],
            [f"{SCHEMA}.suite_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "test_suite_executions",
        sa.Column("test_suite_id", sa.Text(), nullable=False),
        sa.Column("test_suite_code", sa.Text(), nullable=False),
        sa.Column("test_suite_description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("invocation_id", sa.Text(), nullable=True),
        sa.Column("vars_init_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("include_previous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requested_test_id", sa.Text(), nullable=True),
        sa.Column("requested_test_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_suite_id"],
            [f"{SCHEMA}.test_suites.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invocation_id"],
            [f"{SCHEMA}.mock_server_invocations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "suite_item_executions",
        sa.Column("test_suite_execution_id", sa.Text(), nullable=False),
        sa.Column("suite_item_id", sa.Text(), nullable=True),
        sa.Column("item_kind", sa.Text(), nullable=False),
        sa.Column("hook_phase", sa.Text(), nullable=True),
        sa.Column("item_code", sa.Text(), nullable=False),
        sa.Column("item_description", sa.Text(), nullable=True),
        sa.Column("position", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_suite_execution_id"],
            [f"{SCHEMA}.test_suite_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "suite_item_operation_executions",
        sa.Column("test_suite_execution_id", sa.Text(), nullable=False),
        sa.Column("suite_item_execution_id", sa.Text(), nullable=False),
        sa.Column("suite_item_id", sa.Text(), nullable=True),
        sa.Column("suite_item_operation_id", sa.Text(), nullable=True),
        sa.Column("operation_code", sa.Text(), nullable=False),
        sa.Column("operation_description", sa.Text(), nullable=True),
        sa.Column("operation_order", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_suite_execution_id"],
            [f"{SCHEMA}.test_suite_executions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["suite_item_execution_id"],
            [f"{SCHEMA}.suite_item_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    _drop_table_if_exists("suite_item_operation_executions")
    _drop_table_if_exists("suite_item_executions")
    _drop_table_if_exists("test_suite_executions")
    _drop_table_if_exists("suite_item_operations")
    _drop_table_if_exists("suite_items")
    _drop_table_if_exists("test_suites")

    op.create_table(
        "scenarios",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "steps",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("step_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "scenario_steps",
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("step_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False),
        sa.Column("on_failure", sa.Text(), nullable=False, server_default="ABORT"),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], [f"{SCHEMA}.scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "step_operations",
        sa.Column("scenario_step_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_step_id"],
            [f"{SCHEMA}.scenario_steps.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "scenario_executions",
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("scenario_code", sa.Text(), nullable=False),
        sa.Column("scenario_description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("invocation_id", sa.Text(), nullable=True),
        sa.Column("vars_init_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("include_previous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requested_step_id", sa.Text(), nullable=True),
        sa.Column("requested_step_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], [f"{SCHEMA}.scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invocation_id"], [f"{SCHEMA}.mock_server_invocations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "scenario_step_executions",
        sa.Column("scenario_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_id", sa.Text(), nullable=True),
        sa.Column("step_code", sa.Text(), nullable=False),
        sa.Column("step_description", sa.Text(), nullable=True),
        sa.Column("step_order", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_execution_id"],
            [f"{SCHEMA}.scenario_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "step_operation_executions",
        sa.Column("scenario_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_id", sa.Text(), nullable=True),
        sa.Column("step_operation_id", sa.Text(), nullable=True),
        sa.Column("operation_code", sa.Text(), nullable=False),
        sa.Column("operation_description", sa.Text(), nullable=True),
        sa.Column("operation_order", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_execution_id"],
            [f"{SCHEMA}.scenario_executions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_step_execution_id"],
            [f"{SCHEMA}.scenario_step_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
