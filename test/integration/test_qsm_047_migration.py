"""Integration tests for the qsm_047 migration: Test Suites refactor
foundation (schema additions + hook 4 -> 2 collapse).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from docker.errors import DockerException
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.postgres import PostgresContainer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "quality_flow_service"

REVISION_BEFORE = "a9c8d7e6f5b4"   # qsm_044
REVISION_TARGET = "b1c2d3e4f5a6"   # qsm_047

EXPECTED_NEW_SUITE_ITEM_COLUMNS = {
    "role",
    "template_kind",
    "template_config",
    "data_driven",
    "dataset_id",
}
EXPECTED_NEW_EXECUTION_COLUMNS = {
    "parent_execution_id",
    "row_index",
    "row_snapshot",
}
EXPECTED_INDEXES = {
    "suite_items": {"idx_suite_items_role"},
    "suite_item_executions": {"idx_executions_parent"},
}


def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


def _build_alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def _seed_legacy_suite_with_four_hooks(engine) -> None:
    """Populate a fresh qsm_044 schema with one suite that exercises every
    legacy hook phase plus a normal test item. Commands are added with
    explicit `order` so the collapse can verify re-numbering."""
    metadata = MetaData()
    test_suites = Table("test_suites", metadata, schema=SCHEMA, autoload_with=engine)
    suite_items = Table("suite_items", metadata, schema=SCHEMA, autoload_with=engine)
    suite_item_commands = Table(
        "suite_item_commands", metadata, schema=SCHEMA, autoload_with=engine
    )

    with engine.begin() as conn:
        conn.execute(
            test_suites.insert().values(
                id="suite-1",
                code="suite-1",
                description="suite under test",
            )
        )
        for item_id, kind, hook_phase, position in [
            ("item-before-all",  "hook", "before-all",  0),
            ("item-before-each", "hook", "before-each", 1),
            ("item-test",        "test", None,          2),
            ("item-after-each",  "hook", "after-each",  3),
            ("item-after-all",   "hook", "after-all",   4),
        ]:
            conn.execute(
                suite_items.insert().values(
                    id=item_id,
                    test_suite_id="suite-1",
                    kind=kind,
                    hook_phase=hook_phase,
                    code=item_id,
                    description=item_id,
                    position=position,
                    on_failure="ABORT",
                    sources_json=json.dumps([]),
                )
            )
        # Two commands per hook item; one for the test. order=0,1 locally.
        for owner in [
            "item-before-all",
            "item-before-each",
            "item-after-each",
            "item-after-all",
        ]:
            for idx in (0, 1):
                conn.execute(
                    suite_item_commands.insert().values(
                        id=f"cmd-{owner}-{idx}",
                        suite_item_id=owner,
                        code=f"cmd-{owner}-{idx}",
                        description=f"{owner} step {idx}",
                        command_code="setVariable",
                        command_type="action",
                        configuration_json=json.dumps({"name": owner, "value": idx}),
                        order=idx,
                    )
                )
        conn.execute(
            suite_item_commands.insert().values(
                id="cmd-test",
                suite_item_id="item-test",
                code="cmd-test",
                description="test step",
                command_code="setVariable",
                command_type="action",
                configuration_json=json.dumps({}),
                order=0,
            )
        )


def _columns(engine, table: str) -> set[str]:
    return {
        str(c.get("name") or "").strip()
        for c in inspect(engine).get_columns(table, schema=SCHEMA)
    }


def _index_names(engine, table: str) -> set[str]:
    return {
        str(ix.get("name") or "")
        for ix in inspect(engine).get_indexes(table, schema=SCHEMA)
    }


def test_qsm_047_adds_columns_indexes_and_collapses_hooks_four_to_two():
    container = PostgresContainer("postgres:16-alpine")
    started = _start_container_or_skip(container, "postgres")
    previous = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started.get_connection_url()
        cfg = _build_alembic_config()
        command.upgrade(cfg, REVISION_BEFORE)

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            _seed_legacy_suite_with_four_hooks(engine)
            command.upgrade(cfg, REVISION_TARGET)

            assert EXPECTED_NEW_SUITE_ITEM_COLUMNS.issubset(
                _columns(engine, "suite_items")
            )
            assert EXPECTED_NEW_EXECUTION_COLUMNS.issubset(
                _columns(engine, "suite_item_executions")
            )
            for table, expected in EXPECTED_INDEXES.items():
                assert expected.issubset(_index_names(engine, table))

            metadata = MetaData()
            suite_items = Table("suite_items", metadata, schema=SCHEMA, autoload_with=engine)
            suite_item_commands = Table(
                "suite_item_commands", metadata, schema=SCHEMA, autoload_with=engine
            )

            with engine.begin() as conn:
                rows = conn.execute(
                    select(suite_items).where(suite_items.c.test_suite_id == "suite-1")
                ).mappings().all()

                roles = {r["role"] for r in rows}
                assert roles == {"setup", "teardown", "test"}, (
                    f"expected roles to be backfilled to setup/teardown/test, got {roles}"
                )

                hook_items = [r for r in rows if r["kind"] == "hook"]
                assert len(hook_items) == 2, (
                    f"hook 4->2 collapse must leave exactly two hook items per suite, "
                    f"got {len(hook_items)}: {[r['id'] for r in hook_items]}"
                )

                setup_item = next(r for r in hook_items if r["role"] == "setup")
                teardown_item = next(r for r in hook_items if r["role"] == "teardown")
                # The merged item is the highest-priority one (before-all wins).
                assert setup_item["id"] == "item-before-all"
                assert teardown_item["id"] == "item-after-each"

                # Donor items deleted, no backup table per project policy.
                donor_ids = {"item-before-each", "item-after-all"}
                assert not (donor_ids & {r["id"] for r in rows}), (
                    "donor hook suite_items should be deleted after collapse"
                )

                # Commands re-parented: all 4 setup commands belong to the merged
                # setup item, with order 0..3, preserving the original sequence
                # (before-all 0,1 then before-each 0,1).
                setup_commands = conn.execute(
                    select(suite_item_commands)
                    .where(suite_item_commands.c.suite_item_id == setup_item["id"])
                    .order_by(suite_item_commands.c.order)
                ).mappings().all()
                assert [c["order"] for c in setup_commands] == [0, 1, 2, 3]
                assert [c["id"] for c in setup_commands] == [
                    "cmd-item-before-all-0",
                    "cmd-item-before-all-1",
                    "cmd-item-before-each-0",
                    "cmd-item-before-each-1",
                ]

                teardown_commands = conn.execute(
                    select(suite_item_commands)
                    .where(suite_item_commands.c.suite_item_id == teardown_item["id"])
                    .order_by(suite_item_commands.c.order)
                ).mappings().all()
                assert [c["order"] for c in teardown_commands] == [0, 1, 2, 3]
                assert [c["id"] for c in teardown_commands] == [
                    "cmd-item-after-each-0",
                    "cmd-item-after-each-1",
                    "cmd-item-after-all-0",
                    "cmd-item-after-all-1",
                ]

                # The lone test item is unchanged.
                test_item = next(r for r in rows if r["kind"] == "test")
                assert test_item["id"] == "item-test"
                assert test_item["role"] == "test"
                assert test_item["template_kind"] == "custom"
                assert test_item["data_driven"] is False
                assert test_item["template_config"] is None
                assert test_item["dataset_id"] is None
        finally:
            engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        container.stop()


def test_qsm_047_downgrade_removes_new_columns_and_indexes():
    container = PostgresContainer("postgres:16-alpine")
    started = _start_container_or_skip(container, "postgres")
    previous = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started.get_connection_url()
        cfg = _build_alembic_config()
        command.upgrade(cfg, REVISION_TARGET)

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            assert EXPECTED_NEW_SUITE_ITEM_COLUMNS.issubset(_columns(engine, "suite_items"))
            command.downgrade(cfg, REVISION_BEFORE)

            assert not (
                EXPECTED_NEW_SUITE_ITEM_COLUMNS & _columns(engine, "suite_items")
            )
            assert not (
                EXPECTED_NEW_EXECUTION_COLUMNS & _columns(engine, "suite_item_executions")
            )
            for table, removed in EXPECTED_INDEXES.items():
                assert not (removed & _index_names(engine, table))
        finally:
            engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        container.stop()
