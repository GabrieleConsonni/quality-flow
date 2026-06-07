from typing import Any
from uuid import uuid4

from _alembic.models.mock_server_entity import MockServerEntity
from mock_servers.models.runtime_models import (
    MockApiRoute,
    MockCommandSnapshot,
    MockQueueBinding,
    MockRuntimeServer,
)
from mock_servers.services.alembic.mock_server_api_service import MockServerApiService
from mock_servers.services.alembic.mock_server_queue_service import MockServerQueueService
from mock_servers.services.alembic.ms_api_command_service import MsApiOperationService
from mock_servers.services.alembic.ms_queue_command_service import MsQueueOperationService


def _safe_cfg(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_path(path: object) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if len(raw) > 1:
        raw = raw.rstrip("/")
    return raw


def _normalize_endpoint(endpoint: object) -> str:
    return str(endpoint or "").strip().strip("/").lower()


def _build_operation_snapshot(entity) -> MockCommandSnapshot:
    command_code = str(getattr(entity, "command_code", None) or getattr(entity, "operation_type", "") or "")
    command_type = str(getattr(entity, "command_type", "") or "").strip()
    return MockCommandSnapshot(
        id=str(entity.id or ""),
        description=str(entity.description or ""),
        command_code=command_code,
        command_type=command_type,
        configuration_json=_safe_cfg(entity.configuration_json),
        order=int(entity.order or 0),
    )


def _normalize_operation_type(value: object) -> str:
    return str(value or "").strip()


def _extract_operation_cfg(raw_operation: dict[str, Any]) -> dict[str, Any]:
    cfg = raw_operation.get("cfg")
    if isinstance(cfg, dict):
        return cfg

    configuration_json = raw_operation.get("configuration_json")
    if isinstance(configuration_json, dict):
        return configuration_json

    inferred_cfg = dict(raw_operation)
    raw_type = inferred_cfg.get("type") or inferred_cfg.get("commandCode") or inferred_cfg.get("operationType")
    if raw_type and "commandCode" not in inferred_cfg:
        inferred_cfg["commandCode"] = raw_type
    return inferred_cfg


def _build_inline_operation_snapshot(
    raw_operation: dict[str, Any],
    *,
    order: int,
) -> MockCommandSnapshot:
    cfg = _extract_operation_cfg(raw_operation)
    command_code = _normalize_operation_type(cfg.get("commandCode"))
    command_type = str(cfg.get("commandType") or "").strip()
    return MockCommandSnapshot(
        id=str(raw_operation.get("id") or uuid4()),
        description=str(raw_operation.get("description") or ""),
        command_code=command_code,
        command_type=command_type,
        configuration_json=cfg,
        order=int(raw_operation.get("order") or order),
    )


def _parse_inline_operations(value: object) -> list[MockCommandSnapshot]:
    if not isinstance(value, list):
        return []
    result: list[MockCommandSnapshot] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        result.append(_build_inline_operation_snapshot(item, order=index))
    result.sort(key=lambda operation: (operation.order, operation.id))
    return result


def load_runtime_server(session, entity: MockServerEntity) -> MockRuntimeServer:
    endpoint = _normalize_endpoint(entity.endpoint)
    apis_entities = MockServerApiService().get_all_by_server_id(session, entity.id)
    queue_entities = MockServerQueueService().get_all_by_server_id(session, entity.id)

    api_routes: list[MockApiRoute] = []
    for api_entity in apis_entities:
        api_cfg = _safe_cfg(api_entity.configuration_json)
        operations = MsApiOperationService().get_all_by_api_id(session, api_entity.id)
        legacy_operations = [
            _build_operation_snapshot(operation_entity)
            for operation_entity in operations
        ]

        raw_pre_operations = api_cfg.get("pre_response_commands")
        pre_response_operations = _parse_inline_operations(raw_pre_operations)

        raw_post_operations = api_cfg.get("post_response_commands")
        has_explicit_post_operations = isinstance(raw_post_operations, list)
        explicit_post_operations = _parse_inline_operations(
            raw_post_operations
        )

        response_cfg = (
            api_cfg.get("response")
            if isinstance(api_cfg.get("response"), dict)
            else {}
        )
        response_status = response_cfg.get(
            "status",
            api_cfg.get("response_status") or 200,
        )
        response_headers = (
            response_cfg.get("headers")
            if isinstance(response_cfg.get("headers"), dict)
            else (
                api_cfg.get("response_headers")
                if isinstance(api_cfg.get("response_headers"), dict)
                else {}
            )
        )
        response_body = response_cfg.get("body", api_cfg.get("response_body"))

        api_routes.append(
            MockApiRoute(
                id=str(api_entity.id or ""),
                description=str(api_entity.description or ""),
                order=int(api_entity.order or 0),
                method=str(api_entity.method or api_cfg.get("method") or "GET").strip().upper(),
                path=_normalize_path(api_entity.path or api_cfg.get("path")),
                params=api_cfg.get("params") if isinstance(api_cfg.get("params"), dict) else {},
                headers=api_cfg.get("headers") if isinstance(api_cfg.get("headers"), dict) else {},
                body=api_cfg.get("body"),
                body_match=str(api_cfg.get("body_match") or "contains").strip().lower(),
                priority=int(api_cfg.get("priority") or 0),
                response_status=response_status,
                response_headers=response_headers,
                response_body=response_body,
                commands=legacy_operations if not has_explicit_post_operations else [],
                pre_response_commands=pre_response_operations,
                post_response_commands=(
                    explicit_post_operations if has_explicit_post_operations else []
                ),
            )
        )

    queue_bindings: list[MockQueueBinding] = []
    for queue_entity in queue_entities:
        queue_cfg = _safe_cfg(queue_entity.configuration_json)
        operations = MsQueueOperationService().get_all_by_queue_binding_id(
            session,
            queue_entity.id,
        )
        queue_bindings.append(
            MockQueueBinding(
                id=str(queue_entity.id or ""),
                description=str(queue_entity.description or ""),
                order=int(queue_entity.order or 0),
                queue_id=str(queue_entity.queue_id or ""),
                polling_interval_seconds=max(
                    int(queue_cfg.get("polling_interval_seconds") or 1),
                    1,
                ),
                max_messages=max(min(int(queue_cfg.get("max_messages") or 10), 10), 1),
                commands=[
                    _build_operation_snapshot(operation_entity)
                    for operation_entity in operations
                ],
            )
        )

    api_routes.sort(key=lambda item: (item.priority, item.order, item.id))
    queue_bindings.sort(key=lambda item: (item.order, item.id))

    return MockRuntimeServer(
        id=str(entity.id or ""),
        description=str(entity.description or ""),
        endpoint=endpoint,
        is_active=bool(entity.is_active),
        apis=api_routes,
        queues=queue_bindings,
    )

