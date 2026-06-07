import math
from datetime import datetime

from fastapi import APIRouter, Query

from _alembic.models.suite_item_execution_entity import SuiteItemExecutionEntity
from _alembic.models.suite_item_command_execution_entity import (
    SuiteItemOperationExecutionEntity,
)
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from _alembic.services.session_context_manager import managed_session
from elaborations.services.alembic.suite_item_execution_service import (
    SuiteItemExecutionService,
)
from elaborations.services.alembic.suite_item_command_execution_service import (
    SuiteItemOperationExecutionService,
)
from elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from exceptions.app_exception import QualityFlowAppException

router = APIRouter(prefix="/elaborations")


def _serialize_operation_execution(entity: SuiteItemOperationExecutionEntity) -> dict:
    return {
        "id": entity.id,
        "test_suite_execution_id": entity.test_suite_execution_id,
        "suite_item_execution_id": entity.suite_item_execution_id,
        "suite_item_id": entity.suite_item_id,
        "suite_item_command_id": entity.suite_item_operation_id,
        "command_description": entity.operation_description,
        "command_order": int(entity.operation_order),
        "status": entity.status,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
    }


def _serialize_item_execution(session, entity: SuiteItemExecutionEntity, operation_execution_service):
    operations = operation_execution_service.get_all_by_item_execution_id(session, entity.id)
    return {
        "id": entity.id,
        "test_suite_execution_id": entity.test_suite_execution_id,
        "suite_item_id": entity.suite_item_id,
        "item_kind": entity.item_kind,
        "hook_phase": entity.hook_phase,
        "item_description": entity.item_description,
        "position": int(entity.position),
        "status": entity.status,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
        "commands": [_serialize_operation_execution(operation) for operation in operations],
    }


def _serialize_test_suite_execution(
    session,
    entity: TestSuiteExecutionEntity,
    item_execution_service,
    operation_execution_service,
) -> dict:
    items = item_execution_service.get_all_by_execution_id(session, entity.id)
    return {
        "id": entity.id,
        "test_suite_id": entity.test_suite_id,
        "test_suite_description": entity.test_suite_description,
        "status": entity.status,
        "invocation_id": entity.invocation_id,
        "vars_init_json": entity.vars_init_json,
        "result_json": entity.result_json,
        "include_previous": bool(entity.include_previous),
        "requested_test_id": entity.requested_test_id,
        "error_message": entity.error_message,
        "started_at": entity.started_at,
        "finished_at": entity.finished_at,
        "items": [
            _serialize_item_execution(session, item_execution, operation_execution_service)
            for item_execution in items
        ],
    }


@router.get("/test-suite-execution")
async def find_all_test_suite_executions_api(
    test_suite_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    with managed_session() as session:
        execution_service = TestSuiteExecutionService()
        item_execution_service = SuiteItemExecutionService()
        operation_execution_service = SuiteItemOperationExecutionService()
        suite_id = str(test_suite_id or "").strip()
        if suite_id:
            executions = execution_service.get_all_by_suite_id(session, suite_id, limit=limit)
        else:
            executions = execution_service.get_all_ordered(session, limit=limit)
        return [
            _serialize_test_suite_execution(
                session,
                execution,
                item_execution_service,
                operation_execution_service,
            )
            for execution in executions
        ]


@router.get("/test-suite-execution/search")
async def search_test_suite_executions_api(
    test_suite_id: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(success|running|error)$"),
    started_from: datetime | None = Query(default=None),
    started_to: datetime | None = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
):
    with managed_session() as session:
        execution_service = TestSuiteExecutionService()
        item_execution_service = SuiteItemExecutionService()
        operation_execution_service = SuiteItemOperationExecutionService()
        executions, total, resolved_page_number = execution_service.search(
            session,
            test_suite_id=test_suite_id,
            status=status,
            started_from=started_from,
            started_to=started_to,
            page_size=page_size,
            page_number=page_number,
        )
        total_pages = max(1, math.ceil(total / page_size)) if page_size else 1
        return {
            "items": [
                _serialize_test_suite_execution(
                    session,
                    execution,
                    item_execution_service,
                    operation_execution_service,
                )
                for execution in executions
            ],
            "total": total,
            "page_size": page_size,
            "page_number": resolved_page_number,
            "total_pages": total_pages,
        }


@router.get("/test-suite-execution/{execution_id}")
async def find_test_suite_execution_by_id_api(execution_id: str):
    with managed_session() as session:
        execution_service = TestSuiteExecutionService()
        item_execution_service = SuiteItemExecutionService()
        operation_execution_service = SuiteItemOperationExecutionService()
        execution = execution_service.get_by_id(session, execution_id)
        if not execution:
            raise QualityFlowAppException(f"No test suite execution found with id [ {execution_id} ]")
        return _serialize_test_suite_execution(
            session,
            execution,
            item_execution_service,
            operation_execution_service,
        )


@router.delete("/test-suite-execution/{execution_id}")
async def delete_test_suite_execution_by_id_api(execution_id: str):
    with managed_session() as session:
        deleted = TestSuiteExecutionService().delete_by_id(session, execution_id)
        if deleted == 0:
            raise QualityFlowAppException(f"No test suite execution found with id [ {execution_id} ]")
        return {"message": f"{deleted} test suite execution(s) deleted"}

