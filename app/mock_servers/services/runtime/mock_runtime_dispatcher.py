from uuid import uuid4

from fastapi import BackgroundTasks

from _alembic.models.mock_server_invocation_entity import MockServerInvocationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.services.suite_runs.run_context import (
    create_run_context,
    serialize_run_context,
)
from mock_servers.models.runtime_models import MockApiRoute, MockRuntimeServer
from mock_servers.services.alembic.mock_server_invocation_service import (
    MockServerInvocationService,
)
from mock_servers.services.runtime.mock_event_envelope import build_api_event_envelope
from mock_servers.services.runtime.mock_response_builder import (
    build_runtime_response_payload,
)
from mock_servers.services.runtime.mock_server_runtime_registry import (
    MockServerRuntimeRegistry,
)
from mock_servers.services.runtime.mock_runtime_logger import log_mock_server_event
from mock_servers.services.runtime.mock_trigger_executor import execute_mock_operations


def _normalize_path(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if len(raw) > 1:
        raw = raw.rstrip("/")
    return raw


def _to_lowercase_headers(headers: dict[str, str]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value) for key, value in headers.items()}


def _contains(expected, actual) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            if not _contains(expected_value, actual[key]):
                return False
        return True
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        for expected_item in expected:
            if not any(_contains(expected_item, item) for item in actual):
                return False
        return True
    if isinstance(expected, str) and isinstance(actual, str):
        return expected in actual
    return expected == actual


def _map_matches(expected_map: dict, actual_map: dict, *, normalize_keys: bool) -> bool:
    if not expected_map:
        return True
    source_map = (
        {str(key).strip().lower(): value for key, value in actual_map.items()}
        if normalize_keys
        else actual_map
    )
    for key, expected_value in expected_map.items():
        lookup_key = str(key).strip().lower() if normalize_keys else str(key)
        if lookup_key not in source_map:
            return False
        actual_value = source_map.get(lookup_key)
        if str(actual_value) != str(expected_value):
            return False
    return True


def _body_matches(route: MockApiRoute, body_json, body_raw: str) -> bool:
    if route.body is None:
        return True
    if isinstance(route.body, str) and route.body.strip().upper() == "ANY":
        return True
    actual = body_json if body_json is not None else body_raw
    if route.body_match == "equals":
        return route.body == actual
    return _contains(route.body, actual)


def _find_matching_api_route(
    runtime_server: MockRuntimeServer,
    method: str,
    path: str,
    query_params: dict[str, str],
    headers: dict[str, str],
    body_json,
    body_raw: str,
) -> MockApiRoute | None:
    normalized_method = str(method or "").strip().upper()
    normalized_path = _normalize_path(path)
    normalized_headers = _to_lowercase_headers(headers)
    for route in runtime_server.apis:
        if route.method != normalized_method:
            continue
        if route.path != normalized_path:
            continue
        if not _map_matches(route.params, query_params, normalize_keys=False):
            continue
        if not _map_matches(route.headers, normalized_headers, normalize_keys=True):
            continue
        if not _body_matches(route, body_json, body_raw):
            continue
        return route
    return None


def _persist_mock_invocation(
    *,
    mock_server_id: str,
    trigger_type: str,
    event: dict,
) -> str:
    with managed_session() as session:
        return MockServerInvocationService().insert(
            session,
            MockServerInvocationEntity(
                mock_server_id=mock_server_id,
                trigger_type=trigger_type,
                event_json=event if isinstance(event, dict) else {},
            ),
        )


def dispatch_mock_runtime_request(
    *,
    server_endpoint: str,
    method: str,
    path: str,
    query_params: dict[str, str],
    headers: dict[str, str],
    body_raw: str,
    body_json,
    background_tasks: BackgroundTasks,
) -> tuple[int, dict, object] | None:
    runtime_server = MockServerRuntimeRegistry.get_server_by_endpoint(server_endpoint)
    if not runtime_server:
        return None
    route = _find_matching_api_route(
        runtime_server,
        method,
        path,
        query_params,
        headers,
        body_json,
        body_raw,
    )
    if not route:
        return None

    trigger_id = str(uuid4())
    event_payload = body_json if body_json is not None else (body_raw or None)
    event = build_api_event_envelope(
        mock_server_id=runtime_server.id,
        trigger_id=route.id,
        trigger_description=route.description,
        method=method,
        payload=event_payload,
        headers=headers,
        query_params=query_params,
        path_params={},
    )
    invocation_id = _persist_mock_invocation(
        mock_server_id=runtime_server.id,
        trigger_type="api",
        event=event,
    )
    run_context = create_run_context(
        run_id=invocation_id,
        event=event,
        initial_vars={},
        invocation_id=invocation_id,
    )

    pre_response_operations = route.pre_response_commands or []
    if pre_response_operations:
        execute_mock_operations(
            mock_server_id=runtime_server.id,
            trigger_id=trigger_id,
            source_type="api-pre-response",
            source_ref=route.id,
            operations=pre_response_operations,
            data=event_payload,
            run_context=run_context,
            raise_errors=True,
        )

    response_status, response_headers, response_body = build_runtime_response_payload(
        route,
        run_context=run_context,
        trigger_id=trigger_id,
    )

    post_response_operations = route.post_response_commands or route.commands
    if post_response_operations:
        background_tasks.add_task(
            execute_mock_operations,
            mock_server_id=runtime_server.id,
            trigger_id=trigger_id,
            source_type="api",
            source_ref=route.id,
            operations=post_response_operations,
            data=event_payload,
            run_context_payload=serialize_run_context(run_context),
        )

    log_mock_server_event(
        runtime_server.id,
        f"[{trigger_id}] API trigger matched for {method.upper()} {path}",
        payload={
            "trigger_id": trigger_id,
            "invocation_id": invocation_id,
            "method": method.upper(),
            "path": path,
            "api_route_id": route.id,
            "api_route_description": route.description,
        },
    )
    response_headers = dict(response_headers or {})
    response_headers["X-QualityFlow-Trigger-Id"] = trigger_id
    response_headers["X-QualityFlow-Invocation-Id"] = invocation_id
    return (
        int(response_status or 200),
        response_headers,
        response_body,
    )
