import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from _alembic.models.suite_execution_entity import SuiteExecutionEntity
from _alembic.models.suite_test_entity import SuiteTestEntity
from _alembic.models.suite_test_execution_entity import SuiteTestExecutionEntity
from _alembic.services.session_context_manager import managed_session
from config.user_context_config import User, get_current_user_ctx, init_current_user_ctx
from elaborations.models.enums.on_failure import OnFailure
from elaborations.services.alembic.suite_execution_service import SuiteExecutionService
from elaborations.services.alembic.suite_service import SuiteService
from elaborations.services.alembic.suite_test_execution_service import (
    SuiteTestExecutionService,
)
from elaborations.services.alembic.suite_test_service import SuiteTestService
from elaborations.services.suite_runs.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.suite_runs.execution_runtime_context import bind_execution_context
from elaborations.services.suite_runs.run_context import (
    bind_run_context,
    create_run_context,
    serialize_run_context,
)
from elaborations.services.suite_tests.test_executor_composite import execute_test
from exceptions.app_exception import QualityFlowAppException
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


@dataclass
class SuiteExecutionInput:
    execution_id: str
    suite_id: str
    suite_description: str = ""
    event: dict[str, Any] | None = None
    vars_init: dict[str, Any] | None = None
    invocation_id: str | None = None
    target_suite_test_id: str | None = None
    include_previous: bool = False


def log(
    suite_id: str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    payload: dict | list[dict] = None,
):
    log_dto = LogDto(
        subject_type=LogSubjectType.SUITE_EXECUTION,
        subject=suite_id,
        message=message,
        level=level,
        payload=payload,
    )
    LogService().log(log_dto)
    publish_runtime_log_event(
        subject_type=LogSubjectType.SUITE_EXECUTION,
        subject=suite_id,
        level=level,
        message=message,
        payload=payload,
    )


def _resolve_tests_to_execute(
    suite_tests: list[SuiteTestEntity],
    target_suite_test_id: str | None,
    include_previous: bool,
) -> list[SuiteTestEntity]:
    if not target_suite_test_id:
        return suite_tests

    target_index = next(
        (
            idx
            for idx, suite_test in enumerate(suite_tests)
            if str(suite_test.id) == str(target_suite_test_id)
        ),
        -1,
    )
    if target_index < 0:
        raise QualityFlowAppException(
            f"Suite test with id '{target_suite_test_id}' not found in suite"
        )
    if include_previous:
        return suite_tests[: target_index + 1]
    return [suite_tests[target_index]]


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _execute(suite_input: SuiteExecutionInput):
    with managed_session() as session:
        suite_execution_service = SuiteExecutionService()
        suite_test_execution_service = SuiteTestExecutionService()
        suite_label = str(suite_input.suite_description or suite_input.suite_id).strip()

        suite_tests_all: list[SuiteTestEntity] = SuiteTestService().get_all_by_suite_id(
            session, suite_input.suite_id
        )
        target_test_id = str(suite_input.target_suite_test_id or "").strip()

        suite_execution_id = suite_execution_service.insert(
            session,
            SuiteExecutionEntity(
                suite_id=suite_input.suite_id,
                suite_description=suite_input.suite_description,
                status="running",
                invocation_id=str(suite_input.invocation_id or "").strip() or None,
                vars_init_json=(
                    suite_input.vars_init
                    if isinstance(suite_input.vars_init, dict)
                    else {}
                ),
                include_previous=bool(suite_input.include_previous),
                requested_test_id=target_test_id or None,
            ),
        )
        run_context = create_run_context(
            run_id=suite_execution_id,
            event=suite_input.event if isinstance(suite_input.event, dict) else {},
            initial_vars=(
                suite_input.vars_init
                if isinstance(suite_input.vars_init, dict)
                else {}
            ),
            invocation_id=str(suite_input.invocation_id or "").strip() or None,
        )

        with (
            bind_run_context(run_context),
            bind_execution_context(
                execution_id=suite_input.execution_id,
                suite_id=suite_input.suite_id,
                suite_execution_id=suite_execution_id,
            ),
        ):
            results = []
            total_tests = 0
            completed_tests = 0
            error_count = 0
            first_error_message = ""
            try:
                start_message = f"Starting execution of suite '{suite_label}'"
                log(suite_input.suite_id, message=start_message)
                publish_execution_event(
                    suite_input.execution_id,
                    "execution_started",
                    {
                        "suite_execution_id": suite_execution_id,
                        "suite_id": suite_input.suite_id,
                        "suite_description": suite_input.suite_description,
                        "target_suite_test_id": suite_input.target_suite_test_id,
                        "include_previous": suite_input.include_previous,
                    },
                )

                suite_tests = _resolve_tests_to_execute(
                    suite_tests_all,
                    suite_input.target_suite_test_id,
                    suite_input.include_previous,
                )

                total_tests = len(suite_tests)

                publish_execution_event(
                    suite_input.execution_id,
                    "execution_progress",
                    {
                        "suite_execution_id": suite_execution_id,
                        "executed_tests": completed_tests,
                        "total_tests": total_tests,
                    },
                )

                for test_index, suite_test in enumerate(suite_tests, start=1):
                    test_execution_id = suite_test_execution_service.insert(
                        session,
                        SuiteTestExecutionEntity(
                            suite_execution_id=suite_execution_id,
                            suite_test_id=suite_test.id,
                            test_description=str(suite_test.description or ""),
                            test_order=suite_test.order,
                            status="running",
                        ),
                    )

                    test_start_message = (
                        f"Executing suite_test {suite_test.order} "
                        f"of {total_tests} in suite '{suite_label}'"
                    )
                    log(suite_input.suite_id, message=test_start_message)
                    publish_execution_event(
                        suite_input.execution_id,
                        "test_started",
                        {
                            "suite_execution_id": suite_execution_id,
                            "suite_test_execution_id": test_execution_id,
                            "suite_test_id": suite_test.id,
                            "test_description": str(suite_test.description or ""),
                            "test_order": int(suite_test.order),
                            "test_index": test_index,
                            "total_tests": total_tests,
                        },
                    )

                    try:
                        with bind_execution_context(
                            suite_test_id=suite_test.id,
                            suite_test_execution_id=test_execution_id,
                        ):
                            test_results = execute_test(session, suite_test)
                        results.append(test_results)
                        completed_tests += 1
                        suite_test_execution_service.update(
                            session,
                            test_execution_id,
                            status="success",
                            error_message=None,
                            finished_at=_utc_now(),
                        )
                        publish_execution_event(
                            suite_input.execution_id,
                            "test_finished",
                            {
                                "suite_execution_id": suite_execution_id,
                                "suite_test_execution_id": test_execution_id,
                                "suite_test_id": suite_test.id,
                                "test_description": str(suite_test.description or ""),
                                "test_order": int(suite_test.order),
                                "status": "success",
                                "result": test_results,
                            },
                        )
                    except Exception as test_exception:
                        error_count += 1
                        if not first_error_message:
                            first_error_message = str(test_exception)
                        error_message = (
                            f"Error executing suite_test n.'{suite_test.order}' "
                            f"in suite '{suite_label}'"
                        )
                        log(
                            suite_input.suite_id,
                            message=error_message,
                            level=LogLevel.ERROR,
                            payload={"error": str(test_exception)},
                        )
                        suite_test_execution_service.update(
                            session,
                            test_execution_id,
                            status="error",
                            error_message=str(test_exception),
                            finished_at=_utc_now(),
                        )
                        publish_execution_event(
                            suite_input.execution_id,
                            "test_finished",
                            {
                                "suite_execution_id": suite_execution_id,
                                "suite_test_execution_id": test_execution_id,
                                "suite_test_id": suite_test.id,
                                "test_description": str(suite_test.description or ""),
                                "test_order": int(suite_test.order),
                                "status": "error",
                                "error": str(test_exception),
                            },
                        )
                        if suite_test.on_failure == OnFailure.ABORT:
                            break
                    finally:
                        publish_execution_event(
                            suite_input.execution_id,
                            "execution_progress",
                            {
                                "suite_execution_id": suite_execution_id,
                                "executed_tests": completed_tests,
                                "total_tests": total_tests,
                            },
                        )

                finish_message = f"Finished execution of suite '{suite_label}'"
                log(
                    suite_input.suite_id,
                    message=finish_message,
                    payload={"results": results},
                )
            except Exception as suite_exception:
                error_count += 1
                if not first_error_message:
                    first_error_message = str(suite_exception)
                log(
                    suite_input.suite_id,
                    message=f"Suite execution failed for '{suite_label}'",
                    level=LogLevel.ERROR,
                    payload={"error": str(suite_exception)},
                )
            finally:
                execution_status = "error" if error_count > 0 else "success"
                suite_execution_service.update(
                    session,
                    suite_execution_id,
                    status=execution_status,
                    error_message=(first_error_message or None) if error_count > 0 else None,
                    result_json={
                        "results": results,
                        "artifacts": serialize_run_context(run_context).get("artifacts", {}),
                    },
                    finished_at=_utc_now(),
                )

                payload = {
                    "suite_execution_id": suite_execution_id,
                    "suite_id": suite_input.suite_id,
                    "suite_description": suite_input.suite_description,
                    "status": execution_status,
                    "results": results,
                    "errors": error_count,
                    "executed_tests": completed_tests,
                    "total_tests": total_tests,
                }
                if first_error_message:
                    payload["error"] = first_error_message
                publish_execution_event(
                    suite_input.execution_id,
                    "execution_finished",
                    payload,
                )


class SuiteExecutorThread(threading.Thread):

    def __init__(
        self,
        suite_id: str,
        run_event: dict | None = None,
        vars_init: dict | None = None,
        invocation_id: str | None = None,
        target_suite_test_id: str | None = None,
        include_previous: bool = False,
        tenant_id: str = None,
    ):
        super().__init__(name=f"suite-{suite_id}", daemon=True)
        self.execution_id = str(uuid4())
        self.run_event = run_event if isinstance(run_event, dict) else {}
        self.vars_init = vars_init if isinstance(vars_init, dict) else {}
        self.invocation_id = str(invocation_id or "").strip() or None
        self.target_suite_test_id = target_suite_test_id
        self.include_previous = include_previous
        if tenant_id:
            self._captured_user = User(user_id="system", tenant_id=tenant_id)
        else:
            try:
                self._captured_user = get_current_user_ctx()
            except RuntimeError:
                self._captured_user = None
        with managed_session(tenant_id) as session:
            suite = SuiteService().get_by_id(session, suite_id)
            if not suite:
                message = f"Suite with id '{suite_id}' not found"
                log(suite_id, message=message, level=LogLevel.ERROR)
                raise QualityFlowAppException(message)
            self.suite_id = suite.id
            self.suite_description = str(suite.description or suite.code or suite.id or "")

    def run(self):
        if self._captured_user:
            init_current_user_ctx(self._captured_user)
        _execute(
            SuiteExecutionInput(
                execution_id=self.execution_id,
                suite_id=self.suite_id,
                suite_description=self.suite_description,
                event=self.run_event,
                vars_init=self.vars_init,
                invocation_id=self.invocation_id,
                target_suite_test_id=self.target_suite_test_id,
                include_previous=self.include_previous,
            )
        )

