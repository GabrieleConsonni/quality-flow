from typing import Any

from _alembic.models.mock_server_api_entity import MockServerApiEntity
from _alembic.models.mock_server_entity import MockServerEntity
from _alembic.models.mock_server_queue_entity import MockServerQueueEntity
from _alembic.models.ms_api_command_entity import MsApiOperationEntity
from _alembic.models.ms_queue_command_entity import MsQueueOperationEntity
from mock_servers.models.dtos.mock_server_dto import (
    CreateMockServerDto,
    MockServerApiDto,
    MockServerOperationDto,
    MockServerQueueDto,
    UpdateMockServerDto,
)
from mock_servers.services.alembic.mock_server_api_service import MockServerApiService
from mock_servers.services.alembic.mock_server_queue_service import MockServerQueueService
from mock_servers.services.alembic.mock_server_service import MockServerService
from mock_servers.services.alembic.ms_api_command_service import MsApiOperationService
from mock_servers.services.alembic.ms_queue_command_service import MsQueueOperationService
from elaborations.services.constants.command_constant_definition_registry import (
    ensure_command_id,
    rebuild_mock_constant_definitions,
    validate_mock_server_constant_graph,
)


def _safe_cfg(value: dict | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ensure_inline_command_ids(dto: CreateMockServerDto | UpdateMockServerDto) -> None:
    for api_dto in dto.apis or []:
        cfg = api_dto.cfg
        pre_commands = cfg.pre_response_commands if isinstance(cfg.pre_response_commands, list) else []
        for item in pre_commands:
            if isinstance(item, dict):
                ensure_command_id(item)


def _build_mock_server_entity(dto: CreateMockServerDto | UpdateMockServerDto) -> MockServerEntity:
    entity = MockServerEntity()
    entity.description = str(dto.description or "")
    entity.endpoint = str(dto.cfg.endpoint or "").strip().lower()
    entity.configuration_json = dto.cfg.model_dump()
    entity.is_active = bool(dto.is_active)
    return entity


def _build_api_entity(mock_server_id: str, api_dto: MockServerApiDto) -> MockServerApiEntity:
    entity = MockServerApiEntity()
    entity.mock_server_id = mock_server_id
    entity.description = str(api_dto.description or "")
    entity.order = int(api_dto.order or 0)
    entity.method = str(api_dto.cfg.method or "").strip().upper()
    entity.path = str(api_dto.cfg.path or "").strip()
    entity.configuration_json = api_dto.cfg.model_dump()
    return entity


def _build_queue_entity(
    mock_server_id: str,
    queue_dto: MockServerQueueDto,
) -> MockServerQueueEntity:
    entity = MockServerQueueEntity()
    entity.mock_server_id = mock_server_id
    entity.queue_id = str(queue_dto.queue_id or "").strip()
    entity.description = str(queue_dto.description or "")
    entity.order = int(queue_dto.order or 0)
    entity.configuration_json = queue_dto.cfg.model_dump()
    return entity


def _build_api_operation_entity(
    mock_server_api_id: str,
    op_dto: MockServerOperationDto,
) -> MsApiOperationEntity:
    entity = MsApiOperationEntity()
    entity.mock_server_api_id = mock_server_api_id
    entity.description = str(op_dto.description or "")
    entity.operation_type = str(op_dto.cfg.commandCode or "").strip()
    if hasattr(entity, "command_code"):
        entity.command_code = str(op_dto.cfg.commandCode or "").strip()
    if hasattr(entity, "command_type"):
        entity.command_type = str(op_dto.cfg.commandType or "").strip()
    entity.configuration_json = op_dto.cfg.model_dump()
    entity.order = int(op_dto.order or 0)
    return entity


def _build_queue_operation_entity(
    mock_server_queue_id: str,
    op_dto: MockServerOperationDto,
) -> MsQueueOperationEntity:
    entity = MsQueueOperationEntity()
    entity.mock_server_queue_id = mock_server_queue_id
    entity.description = str(op_dto.description or "")
    entity.operation_type = str(op_dto.cfg.commandCode or "").strip()
    if hasattr(entity, "command_code"):
        entity.command_code = str(op_dto.cfg.commandCode or "").strip()
    if hasattr(entity, "command_type"):
        entity.command_type = str(op_dto.cfg.commandType or "").strip()
    entity.configuration_json = op_dto.cfg.model_dump()
    entity.order = int(op_dto.order or 0)
    return entity


def _insert_mock_server_apis(session, mock_server_id: str, apis: list[MockServerApiDto]):
    api_service = MockServerApiService()
    api_operation_service = MsApiOperationService()
    for api_dto in apis or []:
        api_id = api_service.insert(session, _build_api_entity(mock_server_id, api_dto))
        for op_dto in api_dto.commands or []:
            api_operation_service.insert(
                session,
                _build_api_operation_entity(api_id, op_dto),
            )


def _insert_mock_server_queues(
    session,
    mock_server_id: str,
    queues: list[MockServerQueueDto],
):
    queue_service = MockServerQueueService()
    queue_operation_service = MsQueueOperationService()
    for queue_dto in queues or []:
        queue_binding_id = queue_service.insert(
            session,
            _build_queue_entity(mock_server_id, queue_dto),
        )
        for op_dto in queue_dto.commands or []:
            queue_operation_service.insert(
                session,
                _build_queue_operation_entity(queue_binding_id, op_dto),
            )


def create_mock_server(session, dto: CreateMockServerDto) -> str:
    _ensure_inline_command_ids(dto)
    validate_mock_server_constant_graph(dto)
    mock_server_service = MockServerService()
    existing = mock_server_service.get_by_endpoint(session, dto.cfg.endpoint)
    if existing:
        raise ValueError(f"Mock server endpoint '{dto.cfg.endpoint}' already exists.")
    mock_server_id = mock_server_service.insert(session, _build_mock_server_entity(dto))
    _insert_mock_server_apis(session, mock_server_id, dto.apis or [])
    _insert_mock_server_queues(session, mock_server_id, dto.queues or [])
    rebuild_mock_constant_definitions(session, mock_server_id)
    return mock_server_id


def update_mock_server(session, dto: UpdateMockServerDto) -> MockServerEntity:
    _ensure_inline_command_ids(dto)
    validate_mock_server_constant_graph(dto)
    mock_server_service = MockServerService()
    existing = mock_server_service.get_by_id(session, dto.id)
    if not existing:
        raise ValueError(f"Mock server '{dto.id}' not found.")

    endpoint_conflict = mock_server_service.get_by_endpoint(session, dto.cfg.endpoint)
    if endpoint_conflict and str(endpoint_conflict.id) != str(dto.id):
        raise ValueError(f"Mock server endpoint '{dto.cfg.endpoint}' already exists.")

    mock_server_service.update(
        session,
        dto.id,
        description=str(dto.description or ""),
        endpoint=str(dto.cfg.endpoint or "").strip().lower(),
        configuration_json=dto.cfg.model_dump(),
        is_active=bool(dto.is_active),
    )
    MockServerApiService().delete_by_server_id(session, dto.id)
    MockServerQueueService().delete_by_server_id(session, dto.id)
    _insert_mock_server_apis(session, dto.id, dto.apis or [])
    _insert_mock_server_queues(session, dto.id, dto.queues or [])
    rebuild_mock_constant_definitions(session, dto.id)
    updated = mock_server_service.get_by_id(session, dto.id)
    if not updated:
        raise ValueError(f"Mock server '{dto.id}' not found.")
    return updated


def _serialize_operation(operation) -> dict:
    return {
        "id": operation.id,
        "description": operation.description,
        "command_code": getattr(operation, "command_code", None) or operation.operation_type,
        "command_type": getattr(operation, "command_type", None),
        "configuration_json": _safe_cfg(operation.configuration_json),
        "order": int(operation.order or 0),
    }


def _serialize_api(session, api_entity: MockServerApiEntity) -> dict:
    operations = MsApiOperationService().get_all_by_api_id(session, api_entity.id)
    serialized_commands = [_serialize_operation(operation) for operation in operations]
    return {
        "id": api_entity.id,
        "mock_server_id": api_entity.mock_server_id,
        "description": api_entity.description,
        "method": api_entity.method,
        "path": api_entity.path,
        "order": int(api_entity.order or 0),
        "configuration_json": _safe_cfg(api_entity.configuration_json),
        "commands": serialized_commands,
        "operations": serialized_commands,
    }


def _serialize_queue(session, queue_entity: MockServerQueueEntity) -> dict:
    operations = MsQueueOperationService().get_all_by_queue_binding_id(
        session,
        queue_entity.id,
    )
    serialized_commands = [_serialize_operation(operation) for operation in operations]
    return {
        "id": queue_entity.id,
        "mock_server_id": queue_entity.mock_server_id,
        "queue_id": queue_entity.queue_id,
        "description": queue_entity.description,
        "order": int(queue_entity.order or 0),
        "configuration_json": _safe_cfg(queue_entity.configuration_json),
        "commands": serialized_commands,
        "operations": serialized_commands,
    }


def serialize_mock_server(session, entity: MockServerEntity) -> dict:
    apis = MockServerApiService().get_all_by_server_id(session, entity.id)
    queues = MockServerQueueService().get_all_by_server_id(session, entity.id)
    return {
        "id": entity.id,
        "description": entity.description,
        "endpoint": entity.endpoint,
        "is_active": bool(entity.is_active),
        "configuration_json": _safe_cfg(entity.configuration_json),
        "apis": [_serialize_api(session, api_entity) for api_entity in apis],
        "queues": [_serialize_queue(session, queue_entity) for queue_entity in queues],
    }

