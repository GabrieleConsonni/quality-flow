"""2026032810_QSM_044

Revision ID: a9c8d7e6f5b4
Revises: f7a8b9c0d1e2
Create Date: 2026-03-28 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "a9c8d7e6f5b4"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"
SUITE_ITEMS_TABLE = "suite_items"

IMPACTED_TABLES_DELETE_ORDER: tuple[str, ...] = (
    "command_constant_definitions",
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


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name, schema=SCHEMA):
        return False
    return any(
        str(column.get("name") or "").strip() == column_name
        for column in inspector.get_columns(table_name, schema=SCHEMA)
    )


def _delete_all_rows(table_name: str) -> None:
    if not _has_table(table_name):
        return
    op.execute(sa.text(f'DELETE FROM "{SCHEMA}"."{table_name}"'))


def upgrade() -> None:
    if _has_table(SUITE_ITEMS_TABLE) and not _has_column(SUITE_ITEMS_TABLE, "sources_json"):
        op.add_column(
            SUITE_ITEMS_TABLE,
            sa.Column(
                "sources_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            schema=SCHEMA,
        )
        op.alter_column(
            SUITE_ITEMS_TABLE,
            "sources_json",
            schema=SCHEMA,
            server_default=None,
        )

    for table_name in IMPACTED_TABLES_DELETE_ORDER:
        _delete_all_rows(table_name)


def downgrade() -> None:
    if _has_table(SUITE_ITEMS_TABLE) and _has_column(SUITE_ITEMS_TABLE, "sources_json"):
        op.drop_column(SUITE_ITEMS_TABLE, "sources_json", schema=SCHEMA)
