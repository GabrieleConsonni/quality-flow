"""2026052811_QSM_047 — Test Suites refactor · Foundation (Phase 1)

Schema changes that prepare the Test Suites refactor (capability #1 of the
quality-flow refactor wave). Mirrors §1 of the implementation plan in
quality-flow/docs/analisys/QFW-TEST-SUITE/.

Schema additions
----------------
suite_items:
    role             VARCHAR(16)  NOT NULL DEFAULT 'test'      -- test | setup | teardown
    template_kind    VARCHAR(32)  NOT NULL DEFAULT 'custom'    -- custom | send_verify | mock_assert | ...
    template_config  JSONB        NULL                         -- template form snapshot
    data_driven      BOOLEAN      NOT NULL DEFAULT FALSE       -- iterate per dataset row
    dataset_id       TEXT         NULL  FK json_payloads(id)   -- iteration source (Phase 4)

suite_item_executions:
    parent_execution_id  TEXT     NULL  FK self                -- data-driven parent row
    row_index            INTEGER  NULL                         -- 0-based row index for child execs
    row_snapshot         JSONB    NULL                         -- input row captured at runtime

Indexes
-------
idx_suite_items_role(test_suite_id, role, position)
idx_executions_parent(parent_execution_id)

Hook 4 -> 2 collapse (data migration)
-------------------------------------
Legacy suite_items used `kind='hook'` with `hook_phase IN ('before-all',
'before-each', 'after-each', 'after-all')` to model four lifecycle phases.
The refactor collapses them into two phases (`setup` + `teardown`):

* For every test_suite that has setup-side hooks (`before-all` and/or
  `before-each`), the FIRST item (priority: before-all > before-each, then
  position) is promoted to the single setup item; commands from the other
  donor items are re-parented to it with a fresh `order` sequence; donor
  rows are DELETED.
* Same for teardown-side (`after-each`, `after-all`).

Per explicit user decision (2026-05-28) NO data backup is kept. Recovery
relies on external DB dumps. The collapse is informationally lossy: the
per-test semantics of `before-each` cannot be reconstructed. Run
`scripts/audit_before_each.py` BEFORE applying this migration to identify
suites at risk.

The merged item keeps `kind='hook'` and its original `hook_phase` value
(the highest-priority one) so the legacy runtime continues to work
unchanged; the new `role` column is the authoritative discriminator for
new code paths.

Revision ID: b1c2d3e4f5a6
Revises: a9c8d7e6f5b4
Create Date: 2026-05-28 11:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import bindparam, inspect, text
from sqlalchemy.dialects import postgresql


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a9c8d7e6f5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "quality_flow_service"

SUITE_ITEMS = "suite_items"
SUITE_ITEM_COMMANDS = "suite_item_commands"
SUITE_ITEM_EXECUTIONS = "suite_item_executions"
JSON_PAYLOADS = "json_payloads"

SETUP_PHASES = ("before-all", "before-each")
TEARDOWN_PHASES = ("after-each", "after-all")

HOOK_PRIORITY_SQL = """
    CASE hook_phase
        WHEN 'before-all'  THEN 0
        WHEN 'before-each' THEN 1
        WHEN 'after-each'  THEN 2
        WHEN 'after-all'   THEN 3
        ELSE 99
    END
"""


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name, schema=SCHEMA)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name, schema=SCHEMA):
        return False
    return any(
        str(c.get("name") or "").strip() == column_name
        for c in inspector.get_columns(table_name, schema=SCHEMA)
    )


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name, schema=SCHEMA):
        return False
    return any(
        ix.get("name") == index_name
        for ix in inspector.get_indexes(table_name, schema=SCHEMA)
    )


def _add_suite_items_columns() -> None:
    if not _has_column(SUITE_ITEMS, "role"):
        op.add_column(
            SUITE_ITEMS,
            sa.Column(
                "role",
                sa.String(length=16),
                nullable=False,
                server_default="test",
            ),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEMS, "template_kind"):
        op.add_column(
            SUITE_ITEMS,
            sa.Column(
                "template_kind",
                sa.String(length=32),
                nullable=False,
                server_default="custom",
            ),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEMS, "template_config"):
        op.add_column(
            SUITE_ITEMS,
            sa.Column("template_config", postgresql.JSONB(), nullable=True),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEMS, "data_driven"):
        op.add_column(
            SUITE_ITEMS,
            sa.Column(
                "data_driven",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEMS, "dataset_id"):
        op.add_column(
            SUITE_ITEMS,
            sa.Column(
                "dataset_id",
                sa.Text(),
                sa.ForeignKey(
                    f"{SCHEMA}.{JSON_PAYLOADS}.id", ondelete="SET NULL"
                ),
                nullable=True,
            ),
            schema=SCHEMA,
        )


def _add_executions_columns() -> None:
    if not _has_column(SUITE_ITEM_EXECUTIONS, "parent_execution_id"):
        op.add_column(
            SUITE_ITEM_EXECUTIONS,
            sa.Column(
                "parent_execution_id",
                sa.Text(),
                sa.ForeignKey(
                    f"{SCHEMA}.{SUITE_ITEM_EXECUTIONS}.id", ondelete="SET NULL"
                ),
                nullable=True,
            ),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEM_EXECUTIONS, "row_index"):
        op.add_column(
            SUITE_ITEM_EXECUTIONS,
            sa.Column("row_index", sa.Integer(), nullable=True),
            schema=SCHEMA,
        )
    if not _has_column(SUITE_ITEM_EXECUTIONS, "row_snapshot"):
        op.add_column(
            SUITE_ITEM_EXECUTIONS,
            sa.Column("row_snapshot", postgresql.JSONB(), nullable=True),
            schema=SCHEMA,
        )


def _backfill_role() -> None:
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.{SUITE_ITEMS}
            SET role = CASE
                WHEN kind = 'hook' AND hook_phase IN ('before-all', 'before-each') THEN 'setup'
                WHEN kind = 'hook' AND hook_phase IN ('after-each', 'after-all')   THEN 'teardown'
                ELSE 'test'
            END
            """
        )
    )


def _collapse_phase(suite_id: str, phases: tuple[str, ...]) -> None:
    """Merge all hook items of `suite_id` whose hook_phase IN phases into the
    highest-priority one. Re-number the resulting commands and DELETE the
    donor suite_items."""
    bind = op.get_bind()

    items = bind.execute(
        text(
            f"""
            SELECT id
            FROM {SCHEMA}.{SUITE_ITEMS}
            WHERE test_suite_id = :suite_id
              AND hook_phase IN :phases
            ORDER BY {HOOK_PRIORITY_SQL}, position
            """
        ).bindparams(bindparam("phases", expanding=True)),
        {"suite_id": suite_id, "phases": list(phases)},
    ).fetchall()

    if len(items) < 2:
        return

    target_id = items[0].id
    donor_ids = [row.id for row in items[1:]]

    # Re-parent and re-number ALL commands in the phase (target + donors).
    bind.execute(
        text(
            f"""
            WITH ordered AS (
                SELECT sic.id,
                       ROW_NUMBER() OVER (
                           ORDER BY {HOOK_PRIORITY_SQL.replace('hook_phase', 'si.hook_phase')},
                                    si.position,
                                    sic."order"
                       ) - 1 AS new_order
                FROM {SCHEMA}.{SUITE_ITEM_COMMANDS} sic
                JOIN {SCHEMA}.{SUITE_ITEMS} si ON si.id = sic.suite_item_id
                WHERE si.test_suite_id = :suite_id
                  AND si.hook_phase IN :phases
            )
            UPDATE {SCHEMA}.{SUITE_ITEM_COMMANDS} sic
            SET suite_item_id = :target_id,
                "order" = ordered.new_order
            FROM ordered
            WHERE ordered.id = sic.id
            """
        ).bindparams(bindparam("phases", expanding=True)),
        {"suite_id": suite_id, "phases": list(phases), "target_id": target_id},
    )

    bind.execute(
        text(
            f"""
            DELETE FROM {SCHEMA}.{SUITE_ITEMS}
            WHERE id IN :donor_ids
            """
        ).bindparams(bindparam("donor_ids", expanding=True)),
        {"donor_ids": donor_ids},
    )


def _collapse_hooks_four_to_two() -> None:
    bind = op.get_bind()
    suite_ids = bind.execute(
        text(
            f"""
            SELECT DISTINCT test_suite_id
            FROM {SCHEMA}.{SUITE_ITEMS}
            WHERE hook_phase IN :phases
            """
        ).bindparams(bindparam("phases", expanding=True)),
        {"phases": list(SETUP_PHASES + TEARDOWN_PHASES)},
    ).fetchall()

    for (suite_id,) in suite_ids:
        _collapse_phase(suite_id, SETUP_PHASES)
        _collapse_phase(suite_id, TEARDOWN_PHASES)


def _create_indexes() -> None:
    if not _has_index(SUITE_ITEMS, "idx_suite_items_role"):
        op.create_index(
            "idx_suite_items_role",
            SUITE_ITEMS,
            ["test_suite_id", "role", "position"],
            schema=SCHEMA,
        )
    if not _has_index(SUITE_ITEM_EXECUTIONS, "idx_executions_parent"):
        op.create_index(
            "idx_executions_parent",
            SUITE_ITEM_EXECUTIONS,
            ["parent_execution_id"],
            schema=SCHEMA,
        )


def upgrade() -> None:
    if not _has_table(SUITE_ITEMS):
        # Nothing to migrate on a fresh schema before the suite tables exist.
        return

    _add_suite_items_columns()
    _add_executions_columns()
    _backfill_role()
    _collapse_hooks_four_to_two()
    _create_indexes()


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name, schema=SCHEMA)


def downgrade() -> None:
    """Reverse the schema additions. The hook collapse is NOT reversible:
    the original four-hook rows are gone (no in-app backup, per the
    refactor policy). Restoring those requires an external DB dump."""
    if not _has_table(SUITE_ITEMS):
        return

    _drop_index_if_exists(SUITE_ITEM_EXECUTIONS, "idx_executions_parent")
    _drop_index_if_exists(SUITE_ITEMS, "idx_suite_items_role")

    _drop_column_if_exists(SUITE_ITEM_EXECUTIONS, "row_snapshot")
    _drop_column_if_exists(SUITE_ITEM_EXECUTIONS, "row_index")
    _drop_column_if_exists(SUITE_ITEM_EXECUTIONS, "parent_execution_id")

    _drop_column_if_exists(SUITE_ITEMS, "dataset_id")
    _drop_column_if_exists(SUITE_ITEMS, "data_driven")
    _drop_column_if_exists(SUITE_ITEMS, "template_config")
    _drop_column_if_exists(SUITE_ITEMS, "template_kind")
    _drop_column_if_exists(SUITE_ITEMS, "role")
