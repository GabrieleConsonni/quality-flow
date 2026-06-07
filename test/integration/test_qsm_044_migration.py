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
REVISION_BEFORE_QSM_044 = "f7a8b9c0d1e2"
REVISION_QSM_044 = "a9c8d7e6f5b4"

IMPACTED_TABLES = (
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


def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


def _build_alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def test_qsm_044_upgrade_adds_sources_json_and_clears_impacted_suite_and_mock_tables():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started_container.get_connection_url()
        alembic_cfg = _build_alembic_config()
        command.upgrade(alembic_cfg, REVISION_BEFORE_QSM_044)

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            suite_items = Table("suite_items", metadata, schema=SCHEMA, autoload_with=engine)
            test_suites = Table("test_suites", metadata, schema=SCHEMA, autoload_with=engine)

            with engine.begin() as conn:
                conn.execute(
                    test_suites.insert().values(
                        id="suite-1",
                        description="suite to clear",
                    )
                )
                conn.execute(
                    suite_items.insert().values(
                        id="suite-item-1",
                        test_suite_id="suite-1",
                        kind="test",
                        description="item to clear",
                        position=1,
                        on_failure="ABORT",
                    )
                )

            command.upgrade(alembic_cfg, REVISION_QSM_044)

            inspector = inspect(engine)
            suite_item_columns = {
                str(column.get("name") or "").strip()
                for column in inspector.get_columns("suite_items", schema=SCHEMA)
            }
            assert "sources_json" in suite_item_columns

            metadata_after = MetaData()
            counts = {}
            with engine.begin() as conn:
                for table_name in IMPACTED_TABLES:
                    table = Table(table_name, metadata_after, schema=SCHEMA, autoload_with=engine)
                    counts[table_name] = conn.execute(select(table)).fetchall()

            assert all(not rows for rows in counts.values())
        finally:
            engine.dispose()
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        container.stop()
