import unittest

from app._alembic.models.suite_item_entity import SuiteItemEntity
from app._alembic.models.suite_item_command_entity import SuiteItemOperationEntity
from app._alembic.models.test_suite_entity import TestSuiteEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.models.enums.on_failure import OnFailure
from app.elaborations.models.enums.suite_item_kind import SuiteItemKind
from app.elaborations.services.alembic.suite_item_execution_service import (
    SuiteItemExecutionService,
)
from app.elaborations.services.alembic.suite_item_command_execution_service import (
    SuiteItemOperationExecutionService,
)
from app.elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)
from app.elaborations.services.alembic.suite_item_service import SuiteItemService
from app.elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from app.elaborations.services.alembic.test_suite_service import TestSuiteService
from app.elaborations.services.test_suites.test_suite_executor_thread import (
    TestSuiteExecutionInput,
    _execute,
)
from app.logs.services.alembic.log_service import LogService
from uuid import uuid4


def test_execution(alembic_container):
    with managed_session() as session:
        test_suite_id = TestSuiteService().insert(
            session,
            TestSuiteEntity(
                description="suite execution"
            )
        )
        suite_item_id = SuiteItemService().insert(
            session,
            SuiteItemEntity(
                test_suite_id=test_suite_id,
                kind=SuiteItemKind.TEST.value,
                description="test 1",
                position=0,
                on_failure=OnFailure.ABORT.value,
            )
        )
        SuiteItemOperationService().insert(
            session,
            SuiteItemOperationEntity(
                suite_item_id=suite_item_id,
                description="command 1",
                command_code="initConstant",
                command_type="context",
                configuration_json={
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "target": "$.local.rows",
                    "data": [{"id": 1}],
                },
                order=0,
            )
        )

    _execute(TestSuiteExecutionInput(
        execution_id=str(uuid4()),
        test_suite_id=test_suite_id,
        test_suite_description="suite execution",
    ))

    with managed_session() as session:
        suite_executions = TestSuiteExecutionService().get_all_by_suite_id(
            session,
            test_suite_id=test_suite_id,
            limit=10,
        )
        assert len(suite_executions) == 1
        suite_execution = suite_executions[0]
        assert str(suite_execution.status or "").strip().lower() == "success"
        assert suite_execution.finished_at is not None

        test_executions = SuiteItemExecutionService().get_all_by_execution_id(
            session,
            suite_execution.id,
        )
        assert len(test_executions) == 1
        test_execution = test_executions[0]
        assert str(test_execution.status or "").strip().lower() == "success"
        assert test_execution.finished_at is not None

        operation_executions = SuiteItemOperationExecutionService().get_all_by_item_execution_id(
            session,
            test_execution.id,
        )
        assert len(operation_executions) == 1
        operation_execution = operation_executions[0]
        assert str(operation_execution.status or "").strip().lower() == "success"
        assert operation_execution.finished_at is not None

        logs = LogService().get_logs(session)
        assert len(logs) > 0


def test_execution_with_assert_failure_marks_error_statuses(alembic_container):
    with managed_session() as session:
        test_suite_id = TestSuiteService().insert(
            session,
            TestSuiteEntity(description="suite assert error"),
        )
        suite_item_id = SuiteItemService().insert(
            session,
            SuiteItemEntity(
                test_suite_id=test_suite_id,
                kind=SuiteItemKind.TEST.value,
                description="test assert error",
                position=0,
                on_failure=OnFailure.ABORT.value,
            ),
        )
        SuiteItemOperationService().insert(
            session,
            SuiteItemOperationEntity(
                suite_item_id=suite_item_id,
                description="assert empty",
                command_code="jsonEmpty",
                command_type="assert",
                configuration_json={
                    "commandCode": "jsonEmpty",
                    "commandType": "assert",
                    "evaluated_object_type": "json-data",
                    "actual": [{"id": 1, "code": "A"}],
                    "error_message": "Expected no rows from test.",
                },
                order=0,
            ),
        )

    _execute(
        TestSuiteExecutionInput(
            execution_id=str(uuid4()),
            test_suite_id=test_suite_id,
            test_suite_description="suite assert error",
        )
    )

    with managed_session() as session:
        suite_executions = TestSuiteExecutionService().get_all_by_suite_id(
            session,
            test_suite_id=test_suite_id,
            limit=10,
        )
        assert len(suite_executions) == 1
        suite_execution = suite_executions[0]
        assert str(suite_execution.status or "").strip().lower() == "error"
        assert suite_execution.finished_at is not None
        assert "Expected no rows from test." in str(suite_execution.error_message or "")

        test_executions = SuiteItemExecutionService().get_all_by_execution_id(
            session,
            suite_execution.id,
        )
        assert len(test_executions) == 1
        test_execution = test_executions[0]
        assert str(test_execution.status or "").strip().lower() == "error"
        assert test_execution.finished_at is not None
        assert "Expected no rows from test." in str(test_execution.error_message or "")

        operation_executions = SuiteItemOperationExecutionService().get_all_by_item_execution_id(
            session,
            test_execution.id,
        )
        assert len(operation_executions) == 1
        operation_execution = operation_executions[0]
        assert str(operation_execution.status or "").strip().lower() == "error"
        assert operation_execution.finished_at is not None
        assert "Expected no rows from test." in str(operation_execution.error_message or "")


if __name__ == "__main__":
    unittest.main()

