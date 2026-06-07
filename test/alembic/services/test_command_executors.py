from types import SimpleNamespace
from datetime import date
from uuid import uuid4

import pytest
from docker.errors import DockerException
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.mssql import SqlServerContainer
from testcontainers.oracle import OracleDbContainer
from testcontainers.postgres import PostgresContainer

from app._alembic.models.dataset_entity import DatasetEntity
from app._alembic.models.json_payload_entity import JsonPayloadEntity
from app._alembic.models.command_constant_definition_entity import (
    CommandConstantDefinitionEntity,
)
from app._alembic.services.alembic_config_service import url_from_env
from app._alembic.services.session_context_manager import managed_session
from app.data_sources.models.database_connection_config_types import (
    convert_database_connection_config,
)
from app.data_sources.services.alembic.dataset_service import DatasetService
from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    ExportDatasetConfigurationCommandDto,
    InitConstantConfigurationCommandDto,
    ReadApiConfigurationCommandDto,
    RunSuiteConfigurationCommandDto,
    SaveTableConfigurationCommandDto,
    SendMessageQueueConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
)
from app.elaborations.services.operations.assert_command_executor import (
    AssertOperationExecutor,
)
from app.elaborations.services.operations.command_executor_composite import (
    execute_operations,
)
from app.elaborations.services.operations.export_dataset_command_executor import (
    SaveToExternalDbOperationExecutor,
)
from app.elaborations.services.operations.http_command_executor import (
    HttpOperationExecutor,
)
from app.elaborations.services.operations.init_constant_command_executor import (
    DataOperationExecutor,
)
from app.elaborations.services.operations.run_suite_command_executor import (
    RunSuiteOperationExecutor,
)
from app.elaborations.services.operations.save_table_command_executor import (
    SaveInternalDbOperationExecutor,
)
from app.elaborations.services.operations.send_message_queue_command_executor import (
    PublishToQueueOperationExecutor,
)
from app.json_utils.models.enums.json_type import JsonType
from app.json_utils.services.alembic.json_files_service import JsonFilesService
from app.sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)
from elaborations.services.suite_runs.run_context import bind_run_context, create_run_context


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


@pytest.fixture(scope="module")
def external_sqlserver_container():
    container = SqlServerContainer("mcr.microsoft.com/mssql/server:2022-latest")
    started_container = _start_container_or_skip(container, "sqlserver")
    try:
        yield started_container
    finally:
        started_container.stop()


@pytest.fixture(scope="module")
def external_oracle_container():
    container = OracleDbContainer(
        image="gvenzl/oracle-free:slim",
        oracle_password="1Secure*Password1",
    )
    started_container = _start_container_or_skip(container, "oracle")
    try:
        yield started_container
    finally:
        started_container.stop()


def _new_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _insert_database_connection_payload(session, payload: dict) -> str:
    entity = JsonPayloadEntity(
        description="test database connection",
        json_type=JsonType.DATABASE_CONNECTION.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _insert_json_array_payload(session, payload: list[dict] | dict) -> str:
    entity = JsonPayloadEntity(
        description="test json array",
        json_type=JsonType.JSON_ARRAY.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _insert_dataset_payload(
    session,
    payload: dict,
    perimeter: dict | None = None,
) -> str:
    entity = DatasetEntity(
        description="test dataset",
        configuration_json=payload,
        perimeter=perimeter,
    )
    return DatasetService().insert(session, entity)


def _postgres_connection_payload(container) -> dict:
    return {
        "database_type": "postgres",
        "host": container.get_container_host_ip(),
        "port": int(container.get_exposed_port(5432)),
        "database": container.dbname,
        "db_schema": "public",
        "user": container.username,
        "password": container.password,
    }


def _count_rows(url: str, table_name: str, query: str | None = None) -> int:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            count_query = query or f"SELECT COUNT(*) FROM {table_name}"
            return int(connection.execute(text(count_query)).scalar_one())
    finally:
        engine.dispose()


def _count_rows_from_connection_payload(payload: dict, table_name: str) -> int:
    connection_cfg = convert_database_connection_config(payload)
    engine = create_sqlalchemy_engine(connection_cfg)
    try:
        with engine.connect() as connection:
            return int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    finally:
        engine.dispose()


def _insert_constant_definition(
    session,
    *,
    definition_id: str,
    name: str,
    context_scope: str = "local",
    value_type: str = "json",
    command_id: str = "cmd-def",
    section_type: str = "test",
):
    entity = CommandConstantDefinitionEntity()
    entity.id = definition_id
    entity.owner_type = "test"
    entity.command_id = command_id
    entity.command_order = 1
    entity.section_type = section_type
    entity.name = name
    entity.context_scope = context_scope
    entity.value_type = value_type
    entity.declared_at_order = 1
    session.add(entity)
    session.flush()


def test_read_api_configuration_command_requires_get_method():
    with pytest.raises(ValueError, match="readApi.method must be GET"):
        ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            method="POST",
            url="https://api.example.com/orders",
        )


def test_write_api_configuration_command_rejects_unsupported_method():
    with pytest.raises(ValueError, match="writeApi.method must be one of"):
        WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="GET",
            url="https://api.example.com/orders",
        )


def test_http_configuration_command_preserves_authorization_payload():
    cfg = ReadApiConfigurationCommandDto(
        commandCode="readApi",
        commandType="action",
        url="https://api.example.com/orders",
        authorization={
            "type": "bearer",
            "token": "secret-token",
        },
    )

    assert cfg.model_dump()["authorization"] == {
        "type": "bearer",
        "token": {
            "kind": "literal",
            "value": "secret-token",
            "definitionId": None,
            "fieldPath": None,
            "sourceCode": None,
            "resolver": None,
        },
    }


def test_http_operation_executor_returns_envelope_and_writes_result_constant(monkeypatch):
    import app.elaborations.services.operations.http_command_executor as http_module

    class FakeResponse:
        status_code = 201
        ok = True
        url = "https://api.example.com/orders?tenant=it"
        headers = {"Content-Type": "application/json", "X-Test": "yes"}
        content = b'{"id": 10, "status": "CREATED"}'
        text = '{"id": 10, "status": "CREATED"}'

        def json(self):
            return {"id": 10, "status": "CREATED"}

    captured_request: dict[str, object] = {}

    def _fake_request(**kwargs):
        captured_request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(http_module.requests, "request", _fake_request)
    monkeypatch.setattr(http_module.HttpOperationExecutor, "log", lambda *args, **kwargs: None)
    written_result: dict[str, object] = {}
    monkeypatch.setattr(
        http_module,
        "write_result_constant",
        lambda _session, _result_constant, value: written_result.update(value),
    )

    cfg = WriteApiConfigurationCommandDto(
        commandCode="writeApi",
        commandType="action",
        method="POST",
        url="https://api.example.com/orders",
        queryParams={"tenant": "it"},
        headers={"x-api-key": "secret"},
        body={"code": "A-100"},
        bodyType="json",
        timeoutSeconds=12,
        resultConstant={
            "definitionId": "def-http-result",
            "name": "httpResult",
            "valueType": "json",
        },
    )
    run_context = create_run_context(run_id="run-http-write")

    with bind_run_context(run_context):
        result = HttpOperationExecutor().execute(None, "cmd-http-write", cfg, {"input": True})

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "https://api.example.com/orders"
    assert captured_request["params"] == {"tenant": "it"}
    assert captured_request["headers"] == {"x-api-key": "secret"}
    assert captured_request["json"] == {"code": "A-100"}
    assert result.data == {"input": True}
    assert result.result[0]["status"] == 201
    assert result.result[0]["ok"] is True
    assert written_result["body"] == {"id": 10, "status": "CREATED"}


def test_http_operation_executor_uses_data_for_form_urlencoded_body(monkeypatch):
    import app.elaborations.services.operations.http_command_executor as http_module

    class FakeResponse:
        status_code = 200
        ok = True
        url = "https://api.example.com/oauth/token"
        headers = {"Content-Type": "application/json"}
        content = b'{"ok": true}'
        text = '{"ok": true}'

        def json(self):
            return {"ok": True}

    captured_request: dict[str, object] = {}

    def _fake_request(**kwargs):
        captured_request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(http_module.requests, "request", _fake_request)
    monkeypatch.setattr(http_module.HttpOperationExecutor, "log", lambda *args, **kwargs: None)

    cfg = WriteApiConfigurationCommandDto(
        commandCode="writeApi",
        commandType="action",
        method="POST",
        url="https://api.example.com/oauth/token",
        bodyType="formUrlEncoded",
        body={
            "grant_type": "client_credentials",
            "client_id": "client-1",
        },
    )

    with bind_run_context(create_run_context(run_id="run-http-form-body")):
        result = HttpOperationExecutor().execute(None, "cmd-http-form-body", cfg, {})

    assert captured_request["method"] == "POST"
    assert captured_request["url"] == "https://api.example.com/oauth/token"
    assert captured_request["data"] == {
        "grant_type": "client_credentials",
        "client_id": "client-1",
    }
    assert "json" not in captured_request
    assert captured_request["headers"] == {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    assert result.result[0]["status"] == 200


def test_http_operation_executor_preserves_explicit_content_type_for_form_urlencoded_body(monkeypatch):
    import app.elaborations.services.operations.http_command_executor as http_module

    class FakeResponse:
        status_code = 200
        ok = True
        url = "https://api.example.com/oauth/token"
        headers = {"Content-Type": "application/json"}
        content = b'{"ok": true}'
        text = '{"ok": true}'

        def json(self):
            return {"ok": True}

    captured_request: dict[str, object] = {}

    def _fake_request(**kwargs):
        captured_request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(http_module.requests, "request", _fake_request)
    monkeypatch.setattr(http_module.HttpOperationExecutor, "log", lambda *args, **kwargs: None)

    cfg = WriteApiConfigurationCommandDto(
        commandCode="writeApi",
        commandType="action",
        method="POST",
        url="https://api.example.com/oauth/token",
        headers={"content-type": "text/plain"},
        bodyType="formUrlEncoded",
        body={"grant_type": "client_credentials"},
    )

    with bind_run_context(create_run_context(run_id="run-http-form-custom-content-type")):
        HttpOperationExecutor().execute(None, "cmd-http-form-custom-content-type", cfg, {})

    assert captured_request["data"] == {"grant_type": "client_credentials"}
    assert captured_request["headers"] == {"content-type": "text/plain"}


def test_http_operation_executor_fails_fast_on_http_error(monkeypatch):
    import app.elaborations.services.operations.http_command_executor as http_module

    class FakeResponse:
        status_code = 500
        ok = False
        url = "https://api.example.com/orders"
        headers = {"Content-Type": "text/plain"}
        content = b"boom"
        text = "boom"

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(http_module.requests, "request", lambda **_kwargs: FakeResponse())
    monkeypatch.setattr(http_module.HttpOperationExecutor, "log", lambda *args, **kwargs: None)

    cfg = ReadApiConfigurationCommandDto(
        commandCode="readApi",
        commandType="action",
        url="https://api.example.com/orders",
    )

    with bind_run_context(create_run_context(run_id="run-http-read-error")):
        with pytest.raises(ValueError, match="returned status 500"):
            HttpOperationExecutor().execute(None, "cmd-http-read-error", cfg, [])


def test_send_message_queue_command_executor_sends_flat_messages(monkeypatch, alembic_container):
    import app.elaborations.services.operations.send_message_queue_command_executor as publish_module

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    cfg = SendMessageQueueConfigurationCommandDto(
        commandCode="sendMessageQueue",
        commandType="action",
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-payload"},
    )
    run_context = create_run_context(run_id="run-publish")
    run_context.local_scope["constants"]["payload"] = [
        {"id": 1, "value": "a"},
        {"id": 2, "value": "b"},
    ]

    with managed_session() as session:
        _insert_constant_definition(session, definition_id="def-payload", name="payload", value_type="jsonArray")
        with bind_run_context(run_context):
            result = PublishToQueueOperationExecutor().execute(
                session,
                "cmd-publish",
                cfg,
                [],
            )

    assert len(published_calls) == 1
    assert published_calls[0]["queue_id"] == "queue-1"
    assert published_calls[0]["messages"] == run_context.local_scope["constants"]["payload"]
    assert result.result == [{"message": "Published 2 message(s) to queue 'orders'"}]


def test_send_message_queue_command_executor_applies_message_template_to_json_payload(
    monkeypatch,
    alembic_container,
):
    import app.elaborations.services.operations.send_message_queue_command_executor as publish_module

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    cfg = SendMessageQueueConfigurationCommandDto(
        commandCode="sendMessageQueue",
        commandType="action",
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-json-payload"},
        message_template={
            "forEach": "$.body",
            "fields": ["payload"],
            "constants": [
                {"name": "channel", "kind": "string", "value": "sms"},
                {"name": "enabled", "kind": "boolean", "value": "true"},
            ],
        },
    )
    run_context = create_run_context(run_id="run-publish-template-json")
    run_context.local_scope["constants"]["payload"] = {
        "body": {
            "envelope": {"campaign": "west"},
            "payload": [{"id": "xxx", "desc": "desc"}],
        }
    }

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-json-payload",
            name="payload",
            value_type="json",
        )
        with bind_run_context(run_context):
            PublishToQueueOperationExecutor().execute(session, "cmd-publish-template-json", cfg, [])

    assert published_calls[0]["messages"] == [
        {
            "payload": [{"id": "xxx", "desc": "desc"}],
            "channel": "sms",
            "enabled": True,
        }
    ]


def test_send_message_queue_command_executor_applies_nested_template_and_runtime_constants(
    monkeypatch,
    alembic_container,
):
    import app.elaborations.services.operations.send_message_queue_command_executor as publish_module

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    cfg = SendMessageQueueConfigurationCommandDto(
        commandCode="sendMessageQueue",
        commandType="action",
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-json-nested"},
        message_template={
            "forEach": "$.payload[*].nested[*]",
            "fields": ["payload.field", "field2"],
            "constants": [
                {
                    "name": "requestedBy",
                    "kind": "variable",
                    "value": "$.global.constants.requestedBy",
                },
                {
                    "name": "todayValue",
                    "kind": "function",
                    "value": "today",
                },
            ],
        },
    )
    run_context = create_run_context(run_id="run-publish-template-nested")
    run_context.global_scope["constants"]["requestedBy"] = "qa-user"
    run_context.local_scope["constants"]["payload"] = {
        "payload": [
            {
                "field": "xxx",
                "nested": [{"field2": "yyy"}, {"field2": "zzz"}],
            },
            {
                "field": "aaa",
                "nested": [{"field2": "bbb"}, {"field2": "ccc"}],
            },
        ]
    }

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-json-nested",
            name="payload",
            value_type="json",
        )
        with bind_run_context(run_context):
            PublishToQueueOperationExecutor().execute(session, "cmd-publish-template-nested", cfg, [])

    assert published_calls[0]["messages"] == [
        {
            "payload.field": "xxx",
            "field2": "yyy",
            "requestedBy": "qa-user",
            "todayValue": date.today().isoformat(),
        },
        {
            "payload.field": "xxx",
            "field2": "zzz",
            "requestedBy": "qa-user",
            "todayValue": date.today().isoformat(),
        },
        {
            "payload.field": "aaa",
            "field2": "bbb",
            "requestedBy": "qa-user",
            "todayValue": date.today().isoformat(),
        },
        {
            "payload.field": "aaa",
            "field2": "ccc",
            "requestedBy": "qa-user",
            "todayValue": date.today().isoformat(),
        },
    ]


def test_send_message_queue_command_executor_loads_rows_from_dataset(
    monkeypatch,
    alembic_container,
    external_postgres_container,
):
    import app.elaborations.services.operations.send_message_queue_command_executor as publish_module

    table_name = _new_name("queue_dataset")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, status TEXT, note TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, status, note)
                    VALUES
                        (1, 'READY', 'msg-1'),
                        (2, 'READY', 'msg-2'),
                        (3, 'PENDING', 'skip-me')
                    """
                )
            )
    finally:
        external_engine.dispose()

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(
            session,
            _postgres_connection_payload(external_postgres_container),
        )
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
                "sort": [
                    {"field": "id", "direction": "desc"},
                ],
            },
        )
    cfg = SendMessageQueueConfigurationCommandDto(
        commandCode="sendMessageQueue",
        commandType="action",
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-dataset"},
    )
    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-dataset",
            name="payloadDataset",
            value_type="dataset",
        )
        run_context = create_run_context(run_id="run-publish-dataset")
        run_context.local_scope["constants"]["payloadDataset"] = dataset_id
        with bind_run_context(run_context):
            result = PublishToQueueOperationExecutor().execute(
                session,
                "cmd-publish-dataset",
                cfg,
                [],
            )

    assert len(published_calls) == 1
    assert published_calls[0]["queue_id"] == "queue-1"
    assert published_calls[0]["messages"] == [
        {"id": 2, "status": "READY"},
        {"id": 1, "status": "READY"},
    ]
    assert result.result == [{"message": "Published 2 message(s) to queue 'orders'"}]


def test_send_message_queue_command_executor_dataset_with_no_rows_is_noop(
    monkeypatch,
    alembic_container,
    external_postgres_container,
):
    import app.elaborations.services.operations.send_message_queue_command_executor as publish_module

    table_name = _new_name("queue_empty_dataset")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, status TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, status)
                    VALUES
                        (1, 'PENDING'),
                        (2, 'PENDING')
                    """
                )
            )
    finally:
        external_engine.dispose()

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(
            session,
            _postgres_connection_payload(external_postgres_container),
        )
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
            },
        )
    cfg = SendMessageQueueConfigurationCommandDto(
        commandCode="sendMessageQueue",
        commandType="action",
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-empty-dataset"},
    )
    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-empty-dataset",
            name="emptyDataset",
            value_type="dataset",
        )
        run_context = create_run_context(run_id="run-publish-empty-dataset")
        run_context.local_scope["constants"]["emptyDataset"] = dataset_id
        with bind_run_context(run_context):
            result = PublishToQueueOperationExecutor().execute(
                session,
                "cmd-publish-empty-dataset",
                cfg,
                [],
            )

    assert len(published_calls) == 1
    assert published_calls[0]["messages"] == []
    assert result.result == [{"message": "Published 0 message(s) to queue 'orders'"}]


def test_save_table_command_executor_inserts_rows(alembic_container):
    table_name = _new_name("internal_cmd")
    cfg = SaveTableConfigurationCommandDto(
        commandCode="saveTable",
        commandType="action",
        table_name=table_name,
        sourceConstantRef={"definitionId": "def-rows"},
    )
    run_context = create_run_context(run_id="run-save-table")
    run_context.local_scope["constants"]["rows"] = [
        {"id": 1, "name": "first"},
        {"id": 2, "name": "second"},
    ]

    with managed_session() as session:
        _insert_constant_definition(session, definition_id="def-rows", name="rows", value_type="jsonArray")
        with bind_run_context(run_context):
            result = SaveInternalDbOperationExecutor().execute(
                session,
                "cmd-internal",
                cfg,
                [],
            )

    inserted_rows = _count_rows(url_from_env(), table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_save_table_command_executor_reads_rows_from_dataset(
    alembic_container,
    external_postgres_container,
):
    source_table_name = _new_name("src_dataset_internal")
    target_table_name = _new_name("internal_dataset_rows")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {source_table_name} (id INTEGER, status TEXT, note TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {source_table_name} (id, status, note)
                    VALUES
                        (1, 'READY', 'keep-1'),
                        (2, 'READY', 'keep-2'),
                        (3, 'PENDING', 'skip-me')
                    """
                )
            )
    finally:
        external_engine.dispose()

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(
            session,
            _postgres_connection_payload(external_postgres_container),
        )
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": source_table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
                "sort": [
                    {"field": "id", "direction": "asc"},
                ],
            },
        )
    cfg = SaveTableConfigurationCommandDto(
        commandCode="saveTable",
        commandType="action",
        table_name=target_table_name,
        sourceConstantRef={"definitionId": "def-dataset-rows"},
    )
    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-dataset-rows",
            name="rowsDataset",
            value_type="dataset",
        )
        run_context = create_run_context(run_id="run-save-table-dataset")
        run_context.local_scope["constants"]["rowsDataset"] = dataset_id
        with bind_run_context(run_context):
            result = SaveInternalDbOperationExecutor().execute(
                session,
                "cmd-internal-dataset",
                cfg,
                [],
            )

    inserted_rows = _count_rows(url_from_env(), target_table_name)
    ready_rows = _count_rows(
        url_from_env(),
        target_table_name,
        f"SELECT COUNT(*) FROM {target_table_name} WHERE status = 'READY'",
    )

    assert inserted_rows == 2
    assert ready_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {target_table_name} table"}]


def test_export_dataset_command_executor_postgres(alembic_container, external_postgres_container):
    table_name = _new_name("ext_pg")
    data = [
        {"id": 10, "name": "pg-row-1"},
        {"id": 11, "name": "pg-row-2"},
    ]

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
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = ExportDatasetConfigurationCommandDto(
            commandCode="exportDataset",
            commandType="action",
            connection_id=connection_id,
            table_name=table_name,
            sourceConstantRef={"definitionId": "def-ext-pg"},
        )
        _insert_constant_definition(session, definition_id="def-ext-pg", name="rows", value_type="jsonArray")
        run_context = create_run_context(run_id="run-export-pg")
        run_context.local_scope["constants"]["rows"] = data
        with bind_run_context(run_context):
            result = SaveToExternalDbOperationExecutor().execute(
                session,
                "cmd-external-postgres",
                cfg,
                [],
            )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, f"public.{table_name}")

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_export_dataset_command_executor_postgres_reads_rows_from_dataset(
    alembic_container,
    external_postgres_container,
):
    source_table_name = _new_name("src_dataset_ext")
    target_table_name = _new_name("ext_pg_dataset")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {source_table_name} (id INTEGER, status TEXT, note TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {source_table_name} (id, status, note)
                    VALUES
                        (10, 'READY', 'keep-10'),
                        (11, 'READY', 'keep-11'),
                        (12, 'PENDING', 'skip-12')
                    """
                )
            )
    finally:
        external_engine.dispose()

    connection_payload = _postgres_connection_payload(external_postgres_container)

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": source_table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
                "sort": [
                    {"field": "id", "direction": "asc"},
                ],
            },
        )
    with managed_session() as session:
        cfg = ExportDatasetConfigurationCommandDto(
            commandCode="exportDataset",
            commandType="action",
            connection_id=connection_id,
            table_name=target_table_name,
            sourceConstantRef={"definitionId": "def-ext-dataset"},
        )
        _insert_constant_definition(
            session,
            definition_id="def-ext-dataset",
            name="rowsDataset",
            value_type="dataset",
        )
        run_context = create_run_context(run_id="run-export-pg-dataset")
        run_context.local_scope["constants"]["rowsDataset"] = dataset_id
        with bind_run_context(run_context):
            result = SaveToExternalDbOperationExecutor().execute(
                session,
                "cmd-external-postgres-dataset",
                cfg,
                [],
            )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, f"public.{target_table_name}")

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {target_table_name} table"}]


def test_export_dataset_command_executor_sqlserver(alembic_container, external_sqlserver_container):
    table_name = _new_name("ext_sqls")
    data = [
        {"id": 20, "name": "sql-row-1"},
        {"id": 21, "name": "sql-row-2"},
    ]

    connection_payload = {
        "database_type": "sqlserver",
        "host": external_sqlserver_container.get_container_host_ip(),
        "port": int(external_sqlserver_container.get_exposed_port(1433)),
        "database": external_sqlserver_container.dbname,
        "db_schema": "dbo",
        "user": external_sqlserver_container.username,
        "password": external_sqlserver_container.password,
    }

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = ExportDatasetConfigurationCommandDto(
            commandCode="exportDataset",
            commandType="action",
            connection_id=connection_id,
            table_name=table_name,
            sourceConstantRef={"definitionId": "def-ext-sql"},
        )
        _insert_constant_definition(session, definition_id="def-ext-sql", name="rows", value_type="jsonArray")
        run_context = create_run_context(run_id="run-export-sql")
        run_context.local_scope["constants"]["rows"] = data
        with bind_run_context(run_context):
            result = SaveToExternalDbOperationExecutor().execute(
                session,
                "cmd-external-sqlserver",
                cfg,
                [],
            )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_run_suite_command_executor_starts_execution(monkeypatch, alembic_container):
    import elaborations.services.test_suites.test_suite_executor_service as suite_service_module

    captured: dict[str, object] = {}

    def _fake_execute_test_suite_by_id(test_suite_id: str, **kwargs):
        captured["suite_id"] = test_suite_id
        captured["kwargs"] = kwargs
        return "exec-run-suite-1"

    monkeypatch.setattr(
        suite_service_module,
        "execute_test_suite_by_id",
        _fake_execute_test_suite_by_id,
    )

    cfg = RunSuiteConfigurationCommandDto(
        commandCode="runSuite",
        commandType="action",
        suite_id="suite-123",
        constantRefs=[{"definitionId": "def-order-id"}],
    )
    run_context = create_run_context(
        run_id="run-1",
        event={"payload": {"orderId": "ORD-100"}},
        initial_vars={},
        invocation_id="inv-1",
    )
    run_context.local_scope["constants"]["order_id"] = "ORD-100"

    with managed_session() as session:
        _insert_constant_definition(session, definition_id="def-order-id", name="order_id", value_type="raw")
        with bind_run_context(run_context):
            result = RunSuiteOperationExecutor().execute(
                session,
                "cmd-run-suite",
                cfg,
                [{"id": 1}],
            )

    assert captured["suite_id"] == "suite-123"
    assert captured["kwargs"]["run_event"] == {"payload": {"orderId": "ORD-100"}}
    assert captured["kwargs"]["invocation_id"] == "inv-1"
    assert captured["kwargs"]["vars_init"] == {"order_id": "ORD-100"}
    assert result.result[0]["suite_id"] == "suite-123"
    assert result.result[0]["execution_id"] == "exec-run-suite-1"
    assert result.result[0]["constants"] == {"order_id": "ORD-100"}


def test_export_dataset_command_executor_oracle(alembic_container, external_oracle_container):
    table_name = _new_name("ext_orcl")
    data = [
        {"id": 30, "name": "ora-row-1"},
        {"id": 31, "name": "ora-row-2"},
    ]
    service_name = external_oracle_container.dbname or "FREEPDB1"

    connection_payload = {
        "database_type": "oracle",
        "host": external_oracle_container.get_container_host_ip(),
        "port": int(external_oracle_container.get_exposed_port(1521)),
        "database": service_name,
        "db_schema": "SYSTEM",
        "user": "system",
        "password": external_oracle_container.oracle_password,
    }

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = ExportDatasetConfigurationCommandDto(
            commandCode="exportDataset",
            commandType="action",
            connection_id=connection_id,
            table_name=table_name,
            sourceConstantRef={"definitionId": "def-ext-oracle"},
        )
        _insert_constant_definition(session, definition_id="def-ext-oracle", name="rows", value_type="jsonArray")
        run_context = create_run_context(run_id="run-export-oracle")
        run_context.local_scope["constants"]["rows"] = data
        with bind_run_context(run_context):
            result = SaveToExternalDbOperationExecutor().execute(
                session,
                "cmd-external-oracle",
                cfg,
                [],
            )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_init_constant_dataset_applies_perimeter(alembic_container, external_postgres_container):
    table_name = _new_name("ext_perimeter")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, status TEXT, note TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, status, note)
                    VALUES
                        (1, 'READY', 'keep-1'),
                        (2, 'READY', 'keep-2'),
                        (3, 'PENDING', 'drop-me')
                    """
                )
            )
    finally:
        external_engine.dispose()

    connection_payload = _postgres_connection_payload(external_postgres_container)

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
                "sort": [
                    {"field": "id", "direction": "desc"},
                ],
            },
        )
    with managed_session() as session:
        cfg = InitConstantConfigurationCommandDto(
            commandCode="initConstant",
            commandType="context",
            definitionId="def-dataset",
            name="rows",
            context="local",
            dataset_id=dataset_id,
        )
        run_context = create_run_context(
            run_id="run-dataset-perimeter",
            event={"payload": {}},
            initial_vars={},
            invocation_id="inv-dataset-perimeter",
        )
        with bind_run_context(run_context):
            result = DataOperationExecutor().execute(
                session,
                "cmd-init-dataset-perimeter",
                cfg,
                [],
            )

    assert result.data == dataset_id
    assert run_context.local_scope["constants"]["rows"] == dataset_id


def test_init_constant_dataset_with_parameter_bindings_stores_structured_payload(
    alembic_container,
    external_postgres_container,
):
    table_name = _new_name("ext_perimeter_params")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, pipeline_id TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, pipeline_id)
                    VALUES
                        (1, 'PIPE-01'),
                        (2, 'PIPE-02')
                    """
                )
            )
    finally:
        external_engine.dispose()

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(
            session,
            _postgres_connection_payload(external_postgres_container),
        )
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            perimeter={
                "parameters": [
                    {
                        "name": "pipelineId",
                        "type": "string",
                        "required": True,
                    }
                ]
            },
        )
        _insert_constant_definition(
            session,
            definition_id="def-pipeline-id",
            name="pipelineId",
            context_scope="global",
            value_type="raw",
        )
        cfg = InitConstantConfigurationCommandDto(
            commandCode="initConstant",
            commandType="context",
            definitionId="def-dataset",
            name="rows",
            context="local",
            dataset_id=dataset_id,
            parameters={
                "pipelineId": {
                    "kind": "constant_ref",
                    "definitionId": "def-pipeline-id",
                }
            },
        )
        run_context = create_run_context(run_id="run-dataset-params")
        run_context.global_scope["constants"]["pipelineId"] = "PIPE-01"
        with bind_run_context(run_context):
            result = DataOperationExecutor().execute(
                session,
                "cmd-init-dataset-params",
                cfg,
                [],
            )

    assert result.data == {
        "dataset_id": dataset_id,
        "parameters": {"pipelineId": "PIPE-01"},
    }
    assert run_context.local_scope["constants"]["rows"] == result.data


def test_resolve_definition_input_data_loads_rows_from_parameterized_dataset_constant(
    alembic_container,
    external_postgres_container,
):
    from app.elaborations.services.operations.command_data_resolver import (
        resolve_definition_input_data,
    )

    table_name = _new_name("dataset_param_rows")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, status TEXT)"))
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, status)
                    VALUES
                        (1, 'READY'),
                        (2, 'PENDING')
                    """
                )
            )
    finally:
        external_engine.dispose()

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(
            session,
            _postgres_connection_payload(external_postgres_container),
        )
        dataset_id = _insert_dataset_payload(
            session,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            perimeter={
                "selected_columns": ["id", "status"],
                "parameters": [
                    {
                        "name": "statusParam",
                        "type": "string",
                        "required": True,
                    }
                ],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "field": "status",
                            "operator": "eq",
                            "value": {"kind": "parameter", "name": "statusParam"},
                        }
                    ],
                },
            },
        )
        _insert_constant_definition(
            session,
            definition_id="def-parameterized-dataset",
            name="rowsDataset",
            value_type="dataset",
        )
        run_context = create_run_context(run_id="run-parameterized-dataset")
        run_context.local_scope["constants"]["rowsDataset"] = {
            "dataset_id": dataset_id,
            "parameters": {"statusParam": "READY"},
        }

        with bind_run_context(run_context):
            rows = resolve_definition_input_data(session, "def-parameterized-dataset", [])

    assert rows == [{"id": 1, "status": "READY"}]


def test_resolve_definition_input_data_raises_for_invalid_dataset_constant_value(alembic_container):
    from app.elaborations.services.operations.command_data_resolver import (
        resolve_definition_input_data,
    )

    run_context = create_run_context(run_id="run-invalid-dataset")
    run_context.local_scope["constants"]["rowsDataset"] = {"dataset_id": "dataset-1"}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-invalid-dataset",
            name="rowsDataset",
            value_type="dataset",
        )
        with bind_run_context(run_context):
            with pytest.raises(
                ValueError,
                match="must resolve to a dataset id string or object",
            ):
                resolve_definition_input_data(session, "def-invalid-dataset", [])


def test_assert_json_not_empty_command_executor_passes(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonNotEmpty",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-json"},
    )
    data = [{"id": 1, "name": "first"}]
    run_context = create_run_context(run_id="run-assert-json")
    run_context.local_scope["constants"]["actualRows"] = data

    with managed_session() as session:
        _insert_constant_definition(session, definition_id="def-assert-json", name="actualRows", value_type="json")
        with bind_run_context(run_context):
            result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-not-empty",
                cfg,
                data,
            )

    assert result.data == data
    assert result.result == [{"message": "Assert 'jsonNotEmpty' passed for 'json-data' data."}]


def test_assert_json_empty_command_executor_fails_with_custom_message(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonEmpty",
        commandType="assert",
        error_message="Expected no rows.",
        actualConstantRef={"definitionId": "def-assert-empty"},
    )
    run_context = create_run_context(run_id="run-assert-empty")
    run_context.local_scope["constants"]["actualRows"] = [{"id": 1}]

    with managed_session() as session:
        _insert_constant_definition(session, definition_id="def-assert-empty", name="actualRows", value_type="json")
        with bind_run_context(run_context):
            with pytest.raises(ValueError, match="Expected no rows."):
                AssertOperationExecutor().execute(
                    session,
                    "cmd-assert-empty",
                    cfg,
                    [{"id": 1}],
                )


def test_assert_json_array_contains_command_executor_uses_expected_json_array(alembic_container):
    with managed_session() as session:
        expected_json_array_id = _insert_json_array_payload(
            session,
            [
                {"id": 1, "code": "A"},
                {"id": 2, "code": "B"},
            ],
        )
        cfg = AssertConfigurationCommandDto(
            commandCode="jsonArrayContains",
            commandType="assert",
            evaluated_object_type="json-data",
            actualConstantRef={"definitionId": "def-assert-array-contains"},
            expected_json_array_id=expected_json_array_id,
            compare_keys=["id", "code"],
        )
        _insert_constant_definition(
            session,
            definition_id="def-assert-array-contains",
            name="actualRows",
            value_type="jsonArray",
        )
        run_context = create_run_context(run_id="run-assert-array-contains")
        run_context.local_scope["constants"]["actualRows"] = [{"id": 2, "code": "B"}]

        with bind_run_context(run_context):
            ok_result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-contains-ok",
                cfg,
                [{"id": 2, "code": "B"}],
            )
        assert ok_result.result == [
            {"message": "Assert 'jsonArrayContains' passed for 'json-data' data."}
        ]

        run_context.local_scope["constants"]["actualRows"] = [{"id": 3, "code": "C"}]
        with bind_run_context(run_context):
            with pytest.raises(ValueError, match="not contained in expected json-array"):
                AssertOperationExecutor().execute(
                    session,
                    "cmd-assert-contains-ko",
                    cfg,
                    [{"id": 3, "code": "C"}],
                )


def test_assert_json_array_equals_command_executor_is_order_insensitive(alembic_container):
    with managed_session() as session:
        expected_json_array_id = _insert_json_array_payload(
            session,
            [
                {"id": 1, "code": "A"},
                {"id": 2, "code": "B"},
            ],
        )
        cfg = AssertConfigurationCommandDto(
            commandCode="jsonArrayEquals",
            commandType="assert",
            evaluated_object_type="json-data",
            actualConstantRef={"definitionId": "def-assert-array-equals"},
            expected_json_array_id=expected_json_array_id,
            compare_keys=["id", "code"],
        )
        _insert_constant_definition(
            session,
            definition_id="def-assert-array-equals",
            name="actualRows",
            value_type="jsonArray",
        )
        run_context = create_run_context(run_id="run-assert-array-equals")
        run_context.local_scope["constants"]["actualRows"] = [{"id": 2, "code": "B"}, {"id": 1, "code": "A"}]

        with bind_run_context(run_context):
            ok_result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-equals-ok",
                cfg,
                [{"id": 2, "code": "B"}, {"id": 1, "code": "A"}],
            )
        assert ok_result.result == [
            {"message": "Assert 'jsonArrayEquals' passed for 'json-data' data."}
        ]

        run_context.local_scope["constants"]["actualRows"] = [{"id": 1, "code": "A"}]
        with bind_run_context(run_context):
            with pytest.raises(ValueError, match="not equal to expected json-array"):
                AssertOperationExecutor().execute(
                    session,
                    "cmd-assert-equals-ko",
                    cfg,
                    [{"id": 1, "code": "A"}],
                )


def test_assert_json_equals_command_executor_resolves_context_refs(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonEquals",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-equals"},
        expected={"$ref": "$.runEnvelope.event.payload.expected"},
    )
    run_context = create_run_context(
        run_id="run-assert-equals",
        event={"payload": {"expected": {"value": 10}}},
        initial_vars={},
        invocation_id=None,
    )
    run_context.run_envelope["constants"]["actual"] = {"value": 10}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-assert-equals",
            name="actual",
            context_scope="runEnvelope",
            value_type="json",
        )
        with bind_run_context(run_context):
            result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-equals",
                cfg,
                [{"ignored": True}],
            )

    assert result.result == [{"message": "Assert 'jsonEquals' passed for 'json-data' data."}]
    assert isinstance(run_context.artifacts.get("asserts"), list)
    assert run_context.artifacts["asserts"][-1]["status"] == "passed"


def test_assert_json_contains_command_executor_passes_on_selected_keys(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonContains",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-contains"},
        expected={"id": 1, "code": "A"},
        compare_keys=["id", "code"],
    )
    run_context = create_run_context(run_id="run-assert-contains")
    run_context.local_scope["constants"]["actualPayload"] = {"id": 1, "code": "A", "extra": True}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-assert-contains",
            name="actualPayload",
            value_type="json",
        )
        with bind_run_context(run_context):
            result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-contains",
                cfg,
                [{"ignored": True}],
            )

    assert result.result == [{"message": "Assert 'jsonContains' passed for 'json-data' data."}]


def test_assert_json_contains_command_executor_resolves_expected_ref_and_fails_on_mismatch(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonContains",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-contains-ref"},
        expected={"$ref": "$.runEnvelope.event.payload.expected"},
        compare_keys=["id", "code"],
    )
    run_context = create_run_context(
        run_id="run-assert-contains-ref",
        event={"payload": {"expected": {"id": 1, "code": "A"}}},
        initial_vars={},
        invocation_id=None,
    )
    run_context.local_scope["constants"]["actualPayload"] = {"id": 1, "code": "B", "extra": True}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-assert-contains-ref",
            name="actualPayload",
            context_scope="local",
            value_type="json",
        )
        with bind_run_context(run_context):
            with pytest.raises(ValueError, match="does not contain expected values"):
                AssertOperationExecutor().execute(
                    session,
                    "cmd-assert-contains-ref",
                    cfg,
                    [{"ignored": True}],
                )


def test_assert_json_empty_command_executor_uses_resolved_actual_object(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonEmpty",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-empty-object"},
    )
    run_context = create_run_context(run_id="run-assert-empty-object")
    run_context.local_scope["constants"]["actualPayload"] = {}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-assert-empty-object",
            name="actualPayload",
            value_type="json",
        )
        with bind_run_context(run_context):
            result = AssertOperationExecutor().execute(
                session,
                "cmd-assert-empty-object",
                cfg,
                [{"ignored": True}],
            )

    assert result.result == [{"message": "Assert 'jsonEmpty' passed for 'json-data' data."}]


def test_assert_json_not_empty_command_executor_uses_resolved_actual_object(alembic_container):
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonNotEmpty",
        commandType="assert",
        evaluated_object_type="json-data",
        actualConstantRef={"definitionId": "def-assert-not-empty-object"},
    )
    run_context = create_run_context(run_id="run-assert-not-empty-object")
    run_context.local_scope["constants"]["actualPayload"] = {}

    with managed_session() as session:
        _insert_constant_definition(
            session,
            definition_id="def-assert-not-empty-object",
            name="actualPayload",
            value_type="json",
        )
        with bind_run_context(run_context):
            with pytest.raises(ValueError, match="expected actual value to be not empty"):
                AssertOperationExecutor().execute(
                    session,
                    "cmd-assert-not-empty-object",
                    cfg,
                    [{"ignored": True}],
                )


def test_assert_json_contains_requires_compare_keys(alembic_container):
    with pytest.raises(ValueError, match="compare_keys is required for jsonContains"):
        AssertConfigurationCommandDto(
            commandCode="jsonContains",
            commandType="assert",
            evaluated_object_type="json-data",
            actualConstantRef={"definitionId": "def-assert-contains-missing-keys"},
            expected={"id": 1},
        )


def test_execute_operations_rejects_legacy_operation_ids(alembic_container):
    with managed_session() as session:
        with pytest.raises(
            TypeError,
            match="Unsupported command input. Commands must be persisted on their owning context.",
        ):
            execute_operations(session, ["missing-op"], [{"id": 1}])
