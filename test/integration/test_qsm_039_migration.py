import os
from datetime import datetime, timezone
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
REVISION_BEFORE_QSM_039 = "e6f7a8b9c0d1"
REVISION_QSM_039 = "f7a8b9c0d1e2"

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


def _filter_existing_columns(table: Table, values: dict) -> dict:
    available_columns = set(table.c.keys())
    return {key: value for key, value in values.items() if key in available_columns}


def test_qsm_039_upgrade_clears_impacted_suite_and_mock_tables():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started_container.get_connection_url()
        alembic_cfg = _build_alembic_config()
        command.upgrade(alembic_cfg, REVISION_BEFORE_QSM_039)

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            test_suites = Table("test_suites", metadata, schema=SCHEMA, autoload_with=engine)
            suite_items = Table("suite_items", metadata, schema=SCHEMA, autoload_with=engine)
            suite_item_commands = Table("suite_item_commands", metadata, schema=SCHEMA, autoload_with=engine)
            test_suite_executions = Table("test_suite_executions", metadata, schema=SCHEMA, autoload_with=engine)
            test_suite_schedules = Table("test_suite_schedules", metadata, schema=SCHEMA, autoload_with=engine)
            queues = Table("queues", metadata, schema=SCHEMA, autoload_with=engine)
            mock_servers = Table("mock_servers", metadata, schema=SCHEMA, autoload_with=engine)
            mock_server_apis = Table("mock_server_apis", metadata, schema=SCHEMA, autoload_with=engine)
            ms_api_commands = Table("ms_api_commands", metadata, schema=SCHEMA, autoload_with=engine)
            mock_server_queues = Table("mock_server_queues", metadata, schema=SCHEMA, autoload_with=engine)
            ms_queue_commands = Table("ms_queue_commands", metadata, schema=SCHEMA, autoload_with=engine)
            mock_server_invocations = Table("mock_server_invocations", metadata, schema=SCHEMA, autoload_with=engine)

            with engine.begin() as conn:
                conn.execute(
                    test_suites.insert().values(
                        **_filter_existing_columns(
                            test_suites,
                            {
                                "id": "suite-1",
                                "code": "SUITE_1",
                                "description": "suite to clear",
                            },
                        )
                    )
                )
                conn.execute(
                    suite_items.insert().values(
                        **_filter_existing_columns(
                            suite_items,
                            {
                                "id": "suite-item-1",
                                "test_suite_id": "suite-1",
                                "kind": "test",
                                "code": "TEST_1",
                                "description": "test item",
                                "position": 1,
                                "on_failure": "ABORT",
                            },
                        )
                    )
                )
                conn.execute(
                    suite_item_commands.insert().values(
                        **_filter_existing_columns(
                            suite_item_commands,
                            {
                                "id": "suite-command-1",
                                "suite_item_id": "suite-item-1",
                                "code": "CMD_SUITE_1",
                                "description": "command to clear",
                                "command_code": "initConstant",
                                "command_type": "context",
                                "operation_type": "initConstant",
                                "configuration_json": {"commandCode": "initConstant"},
                                "order": 1,
                            },
                        )
                    )
                )
                conn.execute(
                    test_suite_executions.insert().values(
                        **_filter_existing_columns(
                            test_suite_executions,
                            {
                                "id": "suite-execution-1",
                                "test_suite_id": "suite-1",
                                "test_suite_code": "SUITE_1",
                                "test_suite_description": "suite to clear",
                                "status": "completed",
                                "vars_init_json": {},
                                "include_previous": False,
                                "started_at": datetime.now(timezone.utc),
                            },
                        )
                    )
                )
                conn.execute(
                    test_suite_schedules.insert().values(
                        **_filter_existing_columns(
                            test_suite_schedules,
                            {
                                "id": "suite-schedule-1",
                                "test_suite_id": "suite-1",
                                "description": "schedule to clear",
                                "active": True,
                                "frequency_unit": "minutes",
                                "frequency_value": 5,
                                "last_status": "idle",
                            },
                        )
                    )
                )
                conn.execute(
                    queues.insert().values(
                        **_filter_existing_columns(
                            queues,
                            {
                                "id": "queue-1",
                                "code": "QUEUE_1",
                                "description": "queue not impacted",
                                "broker_id": "broker-1",
                                "configuration_json": {},
                            },
                        )
                    )
                )
                conn.execute(
                    mock_servers.insert().values(
                        **_filter_existing_columns(
                            mock_servers,
                            {
                                "id": "mock-server-1",
                                "code": "MOCK_1",
                                "description": "mock server to clear",
                                "endpoint": "orders",
                                "configuration_json": {},
                                "is_active": False,
                            },
                        )
                    )
                )
                conn.execute(
                    mock_server_apis.insert().values(
                        **_filter_existing_columns(
                            mock_server_apis,
                            {
                                "id": "mock-api-1",
                                "mock_server_id": "mock-server-1",
                                "code": "API_1",
                                "description": "api to clear",
                                "method": "GET",
                                "path": "/orders",
                                "configuration_json": {},
                                "order": 1,
                            },
                        )
                    )
                )
                conn.execute(
                    ms_api_commands.insert().values(
                        **_filter_existing_columns(
                            ms_api_commands,
                            {
                                "id": "mock-api-command-1",
                                "mock_server_api_id": "mock-api-1",
                                "code": "CMD_API_1",
                                "description": "api command to clear",
                                "command_code": "runSuite",
                                "command_type": "action",
                                "operation_type": "runSuite",
                                "configuration_json": {"commandCode": "runSuite"},
                                "order": 1,
                            },
                        )
                    )
                )
                conn.execute(
                    mock_server_queues.insert().values(
                        **_filter_existing_columns(
                            mock_server_queues,
                            {
                                "id": "mock-queue-1",
                                "mock_server_id": "mock-server-1",
                                "queue_id": "queue-1",
                                "code": "MQ_1",
                                "description": "queue binding to clear",
                                "configuration_json": {},
                                "order": 1,
                            },
                        )
                    )
                )
                conn.execute(
                    ms_queue_commands.insert().values(
                        **_filter_existing_columns(
                            ms_queue_commands,
                            {
                                "id": "mock-queue-command-1",
                                "mock_server_queue_id": "mock-queue-1",
                                "code": "CMD_QUEUE_1",
                                "description": "queue command to clear",
                                "command_code": "runSuite",
                                "command_type": "action",
                                "operation_type": "runSuite",
                                "configuration_json": {"commandCode": "runSuite"},
                                "order": 1,
                            },
                        )
                    )
                )
                conn.execute(
                    mock_server_invocations.insert().values(
                        **_filter_existing_columns(
                            mock_server_invocations,
                            {
                                "id": "mock-invocation-1",
                                "mock_server_id": "mock-server-1",
                                "mock_server_code": "MOCK_1",
                                "trigger_code": "API_1",
                                "trigger_type": "api",
                                "event_json": {},
                                "created_at": datetime.now(timezone.utc),
                            },
                        )
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(alembic_cfg, REVISION_QSM_039)

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            inspector = inspect(engine)
            with engine.connect() as conn:
                impacted_counts = {}
                for table_name in IMPACTED_TABLES:
                    assert inspector.has_table(table_name, schema=SCHEMA)
                    table = Table(table_name, metadata, schema=SCHEMA, autoload_with=engine)
                    impacted_counts[table_name] = len(conn.execute(select(table.c.id)).all())

                queues = Table("queues", metadata, schema=SCHEMA, autoload_with=engine)
                remaining_queues = conn.execute(select(queues.c.id)).all()
        finally:
            engine.dispose()

        assert impacted_counts == {table_name: 0 for table_name in IMPACTED_TABLES}
        assert remaining_queues == [("queue-1",)]
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        started_container.stop()
