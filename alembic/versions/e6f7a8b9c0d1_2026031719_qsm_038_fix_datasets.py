"""2026031719_QSM_038_FIX_DATASETS

Revision ID: e6f7a8b9c0d1
Revises: d5f6a7b8c9d0
Create Date: 2026-03-17 19:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"
JSON_PAYLOADS_TABLE = "json_payloads"
DATASETS_TABLE = "datasets"
DATASET_JSON_TYPE = "database-table"


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table_name, schema=SCHEMA)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    bind = op.get_bind()
    columns = inspect(bind).get_columns(table_name, schema=SCHEMA)
    return any(str(column.get("name") or "") == column_name for column in columns)


def _ensure_datasets_table() -> None:
    if _has_table(DATASETS_TABLE):
        return
    op.create_table(
        DATASETS_TABLE,
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("perimeter", sa.JSON(), nullable=True),
        sa.Column("created_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("modified_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )


def _migrate_legacy_dataset_rows() -> None:
    if not _has_table(JSON_PAYLOADS_TABLE) or not _has_table(DATASETS_TABLE):
        return
    bind = op.get_bind()
    bind.execute(
        text(
            f"""
            INSERT INTO "{SCHEMA}"."{DATASETS_TABLE}" (
                id,
                description,
                configuration_json,
                perimeter,
                created_date,
                modified_date
            )
            SELECT
                jp.id,
                jp.description,
                jp.payload,
                NULL,
                COALESCE(jp.created_date, NOW()),
                COALESCE(jp.modified_date, NOW())
            FROM "{SCHEMA}"."{JSON_PAYLOADS_TABLE}" jp
            WHERE jp.json_type = :json_type
              AND NOT EXISTS (
                  SELECT 1
                  FROM "{SCHEMA}"."{DATASETS_TABLE}" ds
                  WHERE ds.id = jp.id
              )
            """
        ).bindparams(json_type=DATASET_JSON_TYPE)
    )

    if _has_column(JSON_PAYLOADS_TABLE, "json_type"):
        bind.execute(
            text(
                f'DELETE FROM "{SCHEMA}"."{JSON_PAYLOADS_TABLE}" WHERE json_type = :json_type'
            ).bindparams(json_type=DATASET_JSON_TYPE)
        )


def upgrade() -> None:
    _ensure_datasets_table()
    _migrate_legacy_dataset_rows()


def downgrade() -> None:
    if not _has_table(DATASETS_TABLE):
        return
    bind = op.get_bind()
    if _has_table(JSON_PAYLOADS_TABLE):
        bind.execute(
            text(
                f"""
                INSERT INTO "{SCHEMA}"."{JSON_PAYLOADS_TABLE}" (
                    id,
                    description,
                    json_type,
                    payload,
                    created_date,
                    modified_date
                )
                SELECT
                    ds.id,
                    ds.description,
                    :json_type,
                    ds.configuration_json,
                    COALESCE(ds.created_date, NOW()),
                    COALESCE(ds.modified_date, NOW())
                FROM "{SCHEMA}"."{DATASETS_TABLE}" ds
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM "{SCHEMA}"."{JSON_PAYLOADS_TABLE}" jp
                    WHERE jp.id = ds.id
                )
                """
            ).bindparams(json_type=DATASET_JSON_TYPE)
        )
    op.drop_table(DATASETS_TABLE, schema=SCHEMA)
