import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.models.suite_item_execution_entity import SuiteItemExecutionEntity
from _alembic.models.test_suite_execution_entity import TestSuiteExecutionEntity
from _alembic.services.session_context_manager import managed_session
from config.user_context_config import User, get_current_user_ctx, init_current_user_ctx
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.alembic.suite_item_execution_service import (
    SuiteItemExecutionService,
)
from elaborations.services.alembic.suite_item_service import SuiteItemService
from elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.suite_runs.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.suite_runs.execution_runtime_context import bind_execution_context
from elaborations.services.suite_runs.run_context import (
    bind_run_context,
    bind_suite_item_context,
    create_run_context,
    reset_local_context,
    serialize_run_context,
)
from elaborations.services.suite_source_registry import build_visible_sources_for_suite_item
from elaborations.services.test_suites.suite_item_executor import execute_suite_item
from exceptions.app_exception import QualityFlowAppException
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


@dataclass
class TestSuiteExecutionInput:
    __test__ = False

    execution_id: str
    test_suite_id: str
    test_suite_description: str = ""
    event: dict[str, Any] | None = None
    vars_init: dict[str, Any] | None = None
    invocation_id: str | None = None
    target_suite_item_id: str | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def log(test_suite_id: str, message: str, level: LogLevel = LogLevel.INFO, payload: dict | None = None):
    log_dto = LogDto(
        subject_type=LogSubjectType.SUITE_EXECUTION,
        subject=test_suite_id,
        message=message,
        level=level,
        payload=payload,
    )
    LogService().log(log_dto)
    publish_runtime_log_event(
        subject_type=LogSubjectType.SUITE_EXECUTION,
        subject=test_suite_id,
        level=level,
        message=message,
        payload=payload,
    )


def _resolve_tests_to_execute(
    tests: list[SuiteItemEntity],
    target_suite_item_id: str | None,
) -> list[SuiteItemEntity]:
    if not target_suite_item_id:
        return tests
    target_index = next(
        (idx for idx, test in enumerate(tests) if str(test.id) == str(target_suite_item_id)),
        -1,
    )
    if target_index < 0:
        raise QualityFlowAppException(f"Test with id '{target_suite_item_id}' not found in test suite")
    return [tests[target_index]]


def _create_item_execution(
        session,
        item_execution_service: SuiteItemExecutionService,
    *,
    test_suite_execution_id: str,
    suite_item: SuiteItemEntity,
    position: int,
):
    return item_execution_service.insert(
        session,
        SuiteItemExecutionEntity(
            test_suite_execution_id=test_suite_execution_id,
            suite_item_id=suite_item.id,
            item_kind=str(suite_item.kind or ""),
            hook_phase=str(suite_item.hook_phase or "").strip() or None,
            item_description=str(suite_item.description or ""),
            position=position,
            status="running",
        ),
    )


def _execute_item(
    session,
    execution_input: TestSuiteExecutionInput,
    item_execution_service: SuiteItemExecutionService,
    *,
    test_suite_execution_id: str,
    suite_item: SuiteItemEntity,
    position: int,
    local_vars: dict[str, Any] | None,
    visible_sources: dict[str, Any] | None,
):
    item_execution_id = _create_item_execution(
        session,
        item_execution_service,
        test_suite_execution_id=test_suite_execution_id,
        suite_item=suite_item,
        position=position,
    )
    event_prefix = "hook" if str(suite_item.kind or "") == SuiteItemKind.HOOK.value else "test"
    publish_execution_event(
        execution_input.execution_id,
        f"{event_prefix}_started",
        {
            "test_suite_execution_id": test_suite_execution_id,
            "suite_item_execution_id": item_execution_id,
            "suite_item_id": suite_item.id,
            "item_kind": suite_item.kind,
            "hook_phase": suite_item.hook_phase,
            "item_description": suite_item.description,
            "position": position,
        },
    )
    try:
        with (
            bind_execution_context(
                suite_item_id=suite_item.id,
                suite_item_execution_id=item_execution_id,
            ),
            bind_suite_item_context(
                item_kind=str(suite_item.kind or ""),
                hook_phase=str(suite_item.hook_phase or "").strip() or None,
                local_vars=local_vars,
                visible_sources=visible_sources,
            ),
        ):
            results = execute_suite_item(session, suite_item)
        item_execution_service.update(
            session,
            item_execution_id,
            status="success",
            error_message=None,
            finished_at=_utc_now(),
        )
        publish_execution_event(
            execution_input.execution_id,
            f"{event_prefix}_finished",
            {
                "test_suite_execution_id": test_suite_execution_id,
                "suite_item_execution_id": item_execution_id,
                "suite_item_id": suite_item.id,
                "item_kind": suite_item.kind,
                "hook_phase": suite_item.hook_phase,
                "item_description": suite_item.description,
                "status": "success",
                "result": results,
            },
        )
        return {"status": "success", "result": results, "item_execution_id": item_execution_id}
    except Exception as exc:
        item_execution_service.update(
            session,
            item_execution_id,
            status="error",
            error_message=str(exc),
            finished_at=_utc_now(),
        )
        publish_execution_event(
            execution_input.execution_id,
            f"{event_prefix}_finished",
            {
                "test_suite_execution_id": test_suite_execution_id,
                "suite_item_execution_id": item_execution_id,
                "suite_item_id": suite_item.id,
                "item_kind": suite_item.kind,
                "hook_phase": suite_item.hook_phase,
                "item_description": suite_item.description,
                "status": "error",
                "error": str(exc),
            },
        )
        return {"status": "error", "error": str(exc), "item_execution_id": item_execution_id}


def _execute(execution_input: TestSuiteExecutionInput):
    with managed_session() as session:
        test_suite_execution_service = TestSuiteExecutionService()
        suite_item_execution_service = SuiteItemExecutionService()
        suite_item_service = SuiteItemService()
        test_suite = TestSuiteService().get_by_id(session, execution_input.test_suite_id)
        if not test_suite:
            raise QualityFlowAppException(
                f"No test suite found with id [ {execution_input.test_suite_id} ]"
            )
        test_suite_execution_id = test_suite_execution_service.insert(
            session,
            TestSuiteExecutionEntity(
                test_suite_id=execution_input.test_suite_id,
                test_suite_description=execution_input.test_suite_description,
                status="running",
                invocation_id=str(execution_input.invocation_id or "").strip() or None,
                vars_init_json=execution_input.vars_init if isinstance(execution_input.vars_init, dict) else {},
                include_previous=False,
                requested_test_id=str(execution_input.target_suite_item_id or "").strip() or None,
            ),
        )

        run_context = create_run_context(
            run_id=test_suite_execution_id,
            event=execution_input.event if isinstance(execution_input.event, dict) else {},
            initial_vars=execution_input.vars_init if isinstance(execution_input.vars_init, dict) else {},
            invocation_id=str(execution_input.invocation_id or "").strip() or None,
        )
        hooks = {
            phase.value: suite_item_service.get_hook_by_phase(
                session,
                execution_input.test_suite_id,
                phase.value,
            )
            for phase in HookPhase
        }
        tests = _resolve_tests_to_execute(
            suite_item_service.get_all_tests_by_suite_id(session, execution_input.test_suite_id),
            execution_input.target_suite_item_id,
        )
        requested_test = next(
            (
                item
                for item in tests
                if str(item.id) == str(execution_input.target_suite_item_id or "")
            ),
            None,
        )

        total_tests = len(tests)
        executed_tests = 0
        first_error_message = ""
        any_error = False
        execution_position = 0

        with (
            bind_run_context(run_context),
            bind_execution_context(
                execution_id=execution_input.execution_id,
                test_suite_id=execution_input.test_suite_id,
                test_suite_execution_id=test_suite_execution_id,
            ),
        ):
            publish_execution_event(
                execution_input.execution_id,
                    "suite_started",
                    {
                        "test_suite_execution_id": test_suite_execution_id,
                        "test_suite_id": execution_input.test_suite_id,
                        "test_suite_description": execution_input.test_suite_description,
                        "target_test_id": execution_input.target_suite_item_id,
                        "include_previous": False,
                    },
            )
            publish_execution_event(
                execution_input.execution_id,
                "suite_progress",
                {
                    "test_suite_execution_id": test_suite_execution_id,
                    "executed_tests": executed_tests,
                    "total_tests": total_tests,
                },
            )

            before_all = hooks.get(HookPhase.BEFORE_ALL.value)
            if before_all:
                execution_position += 1
                before_all_result = _execute_item(
                    session,
                    execution_input,
                    suite_item_execution_service,
                    test_suite_execution_id=test_suite_execution_id,
                    suite_item=before_all,
                    position=execution_position,
                    local_vars={},
                    visible_sources=build_visible_sources_for_suite_item(
                        before_all=before_all,
                        before_each=hooks.get(HookPhase.BEFORE_EACH.value),
                        current_item=before_all,
                    ),
                )
                if before_all_result["status"] == "error":
                    any_error = True
                    first_error_message = before_all_result["error"]

            if not any_error:
                for test_item in tests:
                    local_context: dict[str, Any] = {}
                    test_failed = False
                    before_each = hooks.get(HookPhase.BEFORE_EACH.value)
                    if before_each:
                        execution_position += 1
                        before_each_result = _execute_item(
                            session,
                            execution_input,
                            suite_item_execution_service,
                            test_suite_execution_id=test_suite_execution_id,
                            suite_item=before_each,
                            position=execution_position,
                            local_vars=local_context,
                            visible_sources=build_visible_sources_for_suite_item(
                                before_all=hooks.get(HookPhase.BEFORE_ALL.value),
                                before_each=before_each,
                                current_item=before_each,
                            ),
                        )
                        if before_each_result["status"] == "error":
                            test_failed = True
                            any_error = True
                            if not first_error_message:
                                first_error_message = before_each_result["error"]

                    execution_position += 1
                    test_result = _execute_item(
                        session,
                        execution_input,
                        suite_item_execution_service,
                        test_suite_execution_id=test_suite_execution_id,
                        suite_item=test_item,
                        position=execution_position,
                        local_vars=local_context,
                        visible_sources=build_visible_sources_for_suite_item(
                            before_all=hooks.get(HookPhase.BEFORE_ALL.value),
                            before_each=hooks.get(HookPhase.BEFORE_EACH.value),
                            current_item=test_item,
                        ),
                    )
                    executed_tests += 1
                    publish_execution_event(
                        execution_input.execution_id,
                        "suite_progress",
                        {
                            "test_suite_execution_id": test_suite_execution_id,
                            "executed_tests": executed_tests,
                            "total_tests": total_tests,
                        },
                    )
                    if test_result["status"] == "error":
                        test_failed = True
                        any_error = True
                        if not first_error_message:
                            first_error_message = test_result["error"]

                    after_each = hooks.get(HookPhase.AFTER_EACH.value)
                    if after_each:
                        execution_position += 1
                        after_each_result = _execute_item(
                            session,
                            execution_input,
                            suite_item_execution_service,
                            test_suite_execution_id=test_suite_execution_id,
                            suite_item=after_each,
                            position=execution_position,
                            local_vars=local_context,
                            visible_sources=build_visible_sources_for_suite_item(
                                before_all=hooks.get(HookPhase.BEFORE_ALL.value),
                                before_each=hooks.get(HookPhase.BEFORE_EACH.value),
                                current_item=after_each,
                            ),
                        )
                        if after_each_result["status"] == "error":
                            test_failed = True
                            any_error = True
                            if not first_error_message:
                                first_error_message = after_each_result["error"]

                    reset_local_context()
                    if test_failed and str(test_item.on_failure or "").upper() == OnFailure.ABORT.value:
                        break

            after_all = hooks.get(HookPhase.AFTER_ALL.value)
            if after_all:
                execution_position += 1
                after_all_result = _execute_item(
                    session,
                    execution_input,
                    suite_item_execution_service,
                    test_suite_execution_id=test_suite_execution_id,
                    suite_item=after_all,
                    position=execution_position,
                    local_vars={},
                    visible_sources=build_visible_sources_for_suite_item(
                        before_all=hooks.get(HookPhase.BEFORE_ALL.value),
                        before_each=hooks.get(HookPhase.BEFORE_EACH.value),
                        current_item=after_all,
                    ),
                )
                if after_all_result["status"] == "error":
                    any_error = True
                    if not first_error_message:
                        first_error_message = after_all_result["error"]

            test_suite_execution_service.update(
                session,
                test_suite_execution_id,
                status="error" if any_error else "success",
                error_message=first_error_message or None,
                finished_at=_utc_now(),
                result_json=serialize_run_context(run_context),
            )
            publish_execution_event(
                execution_input.execution_id,
                "suite_finished",
                {
                    "test_suite_execution_id": test_suite_execution_id,
                    "status": "error" if any_error else "success",
                    "error": first_error_message or None,
                },
            )
            log(
                execution_input.test_suite_id,
                f"Finished execution of suite '{execution_input.test_suite_description or execution_input.test_suite_id}'",
                level=LogLevel.ERROR if any_error else LogLevel.INFO,
                payload={"status": "error" if any_error else "success"},
            )


class TestSuiteExecutorThread(threading.Thread):
    __test__ = False

    def __init__(
        self,
        test_suite_id: str,
        *,
        run_event: dict | None = None,
        vars_init: dict | None = None,
        invocation_id: str | None = None,
        target_suite_item_id: str | None = None,
        tenant_id: str = None,
    ):
        super().__init__(daemon=True)
        self.execution_id = str(uuid4())
        self.test_suite_id = str(test_suite_id or "").strip()
        self.run_event = run_event
        self.vars_init = vars_init
        self.invocation_id = invocation_id
        self.target_suite_item_id = target_suite_item_id
        if tenant_id:
            self._captured_user = User(user_id="system", tenant_id=tenant_id)
        else:
            try:
                self._captured_user = get_current_user_ctx()
            except RuntimeError:
                self._captured_user = None

    def run(self):
        if self._captured_user:
            init_current_user_ctx(self._captured_user)
        with managed_session() as session:
            suite_entity = TestSuiteService().get_by_id(session, self.test_suite_id)
            if not suite_entity:
                raise QualityFlowAppException(f"No test suite found with id [ {self.test_suite_id} ]")
            suite_description = str(suite_entity.description or "")

        _execute(
            TestSuiteExecutionInput(
                execution_id=self.execution_id,
                test_suite_id=self.test_suite_id,
                test_suite_description=suite_description,
                event=self.run_event,
                vars_init=self.vars_init,
                invocation_id=self.invocation_id,
                target_suite_item_id=self.target_suite_item_id,
            )
        )

