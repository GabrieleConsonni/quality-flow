from contextlib import nullcontext
from typing import Any

from _alembic.models.test_operation_entity import TestOperationEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.services.operations.command_executor_composite import execute_operations
from elaborations.services.operations.command_scope import (
    SCOPE_MOCK_POST_RESPONSE,
    SCOPE_MOCK_PRE_RESPONSE,
)
from elaborations.services.suite_runs.run_context import (
    RunContext,
    bind_run_context,
    deserialize_run_context,
)
from logs.models.enums.log_level import LogLevel
from mock_servers.models.runtime_models import MockCommandSnapshot
from mock_servers.services.runtime.mock_runtime_logger import log_mock_server_event


def _normalize_input_data(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _to_test_operation_snapshot(
    source_id: str,
    operation: MockCommandSnapshot,
) -> TestOperationEntity:
    snapshot = TestOperationEntity()
    snapshot.id = operation.id
    snapshot.suite_test_id = source_id or "mock-runtime"
    snapshot.code = operation.id
    snapshot.description = operation.description
    snapshot.operation_type = operation.command_code
    snapshot.configuration_json = operation.configuration_json
    snapshot.order = operation.order
    return snapshot


def _scope_from_source_type(source_type: str) -> str:
    normalized_source_type = str(source_type or "").strip().lower()
    if normalized_source_type == "api-pre-response":
        return SCOPE_MOCK_PRE_RESPONSE
    return SCOPE_MOCK_POST_RESPONSE


def execute_mock_operations(
    *,
    mock_server_id: str,
    trigger_id: str,
    source_type: str,
    source_ref: str,
    operations: list[MockCommandSnapshot],
    data: Any,
    run_context: RunContext | None = None,
    run_context_payload: dict | None = None,
    raise_errors: bool = False,
    tenant_id: str = None,
):
    normalized_data = _normalize_input_data(data)
    snapshots = [
        _to_test_operation_snapshot(source_ref, operation)
        for operation in operations or []
    ]
    if not snapshots:
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] No operations configured for {source_type} trigger.",
        )
        return

    context = run_context or deserialize_run_context(run_context_payload)
    execution_scope = _scope_from_source_type(source_type)
    try:
        with managed_session(tenant_id) as session:
            context_manager = bind_run_context(context) if context else nullcontext()
            with context_manager:
                execute_operations(
                    session,
                    snapshots,
                    normalized_data,
                    execution_scope=execution_scope,
                )
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] Executed {len(snapshots)} command(s) for {source_type} trigger.",
            payload={
                "trigger_id": trigger_id,
                "source_type": source_type,
                "scope": execution_scope,
                "source_ref": source_ref,
                "commands": len(snapshots),
            },
        )
    except Exception as exc:
        log_mock_server_event(
            mock_server_id,
            f"[{trigger_id}] Error executing commands for {source_type}: {str(exc)}",
            level=LogLevel.ERROR,
            payload={
                "trigger_id": trigger_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "error": str(exc),
            },
        )
        if raise_errors:
            raise

