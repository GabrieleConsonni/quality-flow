from types import SimpleNamespace
from uuid import uuid4

import pytest
from docker.errors import DockerException
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.postgres import PostgresContainer

from app._alembic.models.dataset_entity import DatasetEntity
from app._alembic.models.json_payload_entity import JsonPayloadEntity
from app._alembic.services.session_context_manager import managed_session
from app.data_sources.services.alembic.dataset_service import DatasetService
from app.elaborations.models.dtos.configuration_test_dtos import (
    DataConfigurationTestDTO,
    DataFromDbConfigurationTestDto,
    DataFromJsonArrayConfigurationTestDto,
    DataFromQueueConfigurationTestDto,
    SleepConfigurationTestDto,
)
from app.elaborations.services.operations.command_executor import ExecutionResultDto
from app.elaborations.services.suite_tests.data_from_db_test_executor import (
    DataFromDbTestExecutor,
)
from app.elaborations.services.suite_tests.data_from_json_array_test_executor import (
    DataFromJsonArrayTestExecutor,
)
from app.elaborations.services.suite_tests.data_from_queue_test_executor import (
    DataFromQueueTestExecutor,
)
from app.elaborations.services.suite_tests.data_test_executor import DataTestExecutor
from app.elaborations.services.suite_tests.sleep_test_executor import SleepTestExecutor
from app.json_utils.models.enums.json_type import JsonType
from app.json_utils.services.alembic.json_files_service import JsonFilesService


def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


@pytest.fixture(scope="module")
def external_postgres_container():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    try:
        yield started_container
    finally:
        started_container.stop()


def _new_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _insert_json_payload(
    session,
    json_type: JsonType,
    payload: dict | list[dict],
    code_prefix: str,
) -> str:
    entity = JsonPayloadEntity(
        description=f"{code_prefix} test payload",
        json_type=json_type.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _insert_dataset_payload(session, payload: dict, perimeter: dict | None = None) -> str:
    entity = DatasetEntity(
        description="dataset test payload",
        configuration_json=payload,
        perimeter=perimeter,
    )
    return DatasetService().insert(session, entity)


def _patch_execute_operations_for_class(monkeypatch, clazz, captured: dict):
    def _fake_execute_operations(cls, session, test_id, test_code, data):
        captured["test_id"] = test_id
        captured["test_code"] = test_code
        captured["data"] = data
        return [{"message": "ok"}]

    monkeypatch.setattr(clazz, "execute_operations", classmethod(_fake_execute_operations))


def test_sleep_test_executor_returns_slept_status(monkeypatch, alembic_container):
    import app.elaborations.services.suite_tests.sleep_test_executor as sleep_module

    sleep_calls: list[int] = []
    monkeypatch.setattr(sleep_module.time, "sleep", lambda duration: sleep_calls.append(duration))

    suite_test = SimpleNamespace(code="test-1", id="sc-test-0")
    cfg = SleepConfigurationTestDto(duration=2)

    with managed_session() as session:
        result = SleepTestExecutor().execute(session, suite_test, cfg)

    assert sleep_calls == [2]
    assert result == [{"status": "slept", "duration": "2"}]


def test_data_test_executor_forwards_cfg_data(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataTestExecutor, captured)

    suite_test = SimpleNamespace(id="sc-test-1", code="test-1")
    cfg = DataConfigurationTestDTO(data=[{"id": 1}, {"id": 2}])

    with managed_session() as session:
        result = DataTestExecutor().execute(session, suite_test, cfg)

    assert captured["test_id"] == "sc-test-1"
    assert captured["data"] == [{"id": 1}, {"id": 2}]
    assert result == [{"message": "ok"}]


def test_data_from_json_array_test_executor_uses_list_payload(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromJsonArrayTestExecutor, captured)

    with managed_session() as session:
        json_array_id = _insert_json_payload(
            session,
            JsonType.JSON_ARRAY,
            [{"id": 1}, {"id": 2}],
            "json_arr",
        )
        suite_test = SimpleNamespace(id="sc-test-2", code="test-2")
        cfg = DataFromJsonArrayConfigurationTestDto(json_array_id=json_array_id)

        result = DataFromJsonArrayTestExecutor().execute(session, suite_test, cfg)

    assert captured["test_id"] == "sc-test-2"
    assert captured["data"] == [{"id": 1}, {"id": 2}]
    assert result == [{"message": "ok"}]


def test_data_from_json_array_test_executor_wraps_single_object(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromJsonArrayTestExecutor, captured)

    with managed_session() as session:
        json_array_id = _insert_json_payload(
            session,
            JsonType.JSON_ARRAY,
            {"id": 10, "name": "single"},
            "json_obj",
        )
        suite_test = SimpleNamespace(id="sc-test-3", code="test-3")
        cfg = DataFromJsonArrayConfigurationTestDto(json_array_id=json_array_id)

        result = DataFromJsonArrayTestExecutor().execute(session, suite_test, cfg)

    assert captured["data"] == [{"id": 10, "name": "single"}]
    assert result == [{"message": "ok"}]


def test_data_from_queue_test_executor_reads_until_max_messages(monkeypatch, alembic_container):
    import app.elaborations.services.suite_tests.data_from_queue_test_executor as queue_module

    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromQueueTestExecutor, captured)

    queue = SimpleNamespace(code="queue-code", broker_id="broker-1")
    fake_connection_cfg = object()
    sleep_calls: list[int] = []
    receive_max_arguments: list[int] = []
    responses = [[], [{"id": 1}], [{"id": 2}], [{"id": 3}]]

    class FakeQueueConnectionService:
        def receive_messages(self, connection_config, queue_id, max_messages=10):
            receive_max_arguments.append(max_messages)
            if responses:
                return responses.pop(0)
            return []

    monkeypatch.setattr(
        queue_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: queue,
    )
    monkeypatch.setattr(queue_module, "load_broker_connection", lambda _broker_id: fake_connection_cfg)
    monkeypatch.setattr(
        queue_module.QueueConnectionServiceFactory,
        "get_service",
        classmethod(lambda _cls, _cfg: FakeQueueConnectionService()),
    )
    monkeypatch.setattr(queue_module.time, "sleep", lambda duration: sleep_calls.append(duration))

    suite_test = SimpleNamespace(id="sc-test-4", code="test-4")
    cfg = DataFromQueueConfigurationTestDto(
        queue_id="queue-1",
        retry=4,
        wait_time_seconds=1,
        max_messages=3,
    )

    with managed_session() as session:
        result = DataFromQueueTestExecutor().execute(session, suite_test, cfg)

    assert captured["test_id"] == "sc-test-4"
    assert captured["data"] == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert sleep_calls == [1]
    assert receive_max_arguments == [3, 3, 2, 1]
    assert result == [{"message": "ok"}]


def test_data_from_queue_test_executor_raises_when_queue_not_found(alembic_container):
    import app.elaborations.services.suite_tests.data_from_queue_test_executor as queue_module

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(queue_module.QueueService, "get_by_id", lambda _self, _session, _queue_id: None)
    try:
        suite_test = SimpleNamespace(id="sc-test-5", code="test-5")
        cfg = DataFromQueueConfigurationTestDto(queue_id="missing-queue")
        with managed_session() as session:
            with pytest.raises(ValueError, match="Queue 'missing-queue' not found"):
                DataFromQueueTestExecutor().execute(session, suite_test, cfg)
    finally:
        monkeypatch.undo()


def test_data_from_db_test_executor_reads_from_external_postgres(
    monkeypatch,
    alembic_container,
    external_postgres_container,
):
    import app.elaborations.services.suite_tests.data_from_db_test_executor as db_module

    table_name = _new_name("test_db")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, name TEXT)"))
            conn.execute(
                text(f"INSERT INTO {table_name} (id, name) VALUES (1, 'row-1'), (2, 'row-2')")
            )
    finally:
        external_engine.dispose()

    captured: dict = {}

    def _fake_execute_operations(session, operation_ids, data):
        captured["operation_ids"] = operation_ids
        captured["data"] = data
        return [{"message": "db-forwarded"}]

    monkeypatch.setattr(
        db_module.DataFromDbTestExecutor,
        "execute_operations",
        classmethod(
            lambda _cls, session, test_id, test_code, data: _fake_execute_operations(
                session,
                [],
                data,
            )
        ),
    )

    connection_payload = {
        "database_type": "postgres",
        "host": external_postgres_container.get_container_host_ip(),
        "port": int(external_postgres_container.get_exposed_port(5432)),
        "database": external_postgres_container.dbname,
        "db_schema": "public",
        "user": external_postgres_container.username,
        "password": external_postgres_container.password,
    }

    with managed_session() as session:
        connection_id = _insert_json_payload(
            session,
            JsonType.DATABASE_CONNECTION,
            connection_payload,
            "db_conn",
        )
        datasource_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
            },
        )

    with managed_session() as session:
        suite_test = SimpleNamespace(id="sc-test-6", code="test-6", configuration_json={})
        cfg = DataFromDbConfigurationTestDto(dataset_id=datasource_id)
        result = DataFromDbTestExecutor().execute(session, suite_test, cfg)

    assert captured["operation_ids"] == []
    assert len(captured["data"]) == 2
    assert {row["id"] for row in captured["data"]} == {1, 2}
    assert result == [{"message": "db-forwarded"}]

