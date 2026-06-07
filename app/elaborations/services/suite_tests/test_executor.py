from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from elaborations.models.dtos.configuration_test_dtos import ConfigurationTestDtoTypes
from elaborations.services.alembic.test_operation_service import TestOperationService
from elaborations.services.operations.command_executor_composite import execute_operations
from elaborations.services.suite_runs.execution_event_bus import publish_runtime_log_event
from elaborations.services.suite_runs.execution_runtime_context import bind_execution_context
from elaborations.services.suite_runs.run_context import set_context_last
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


class TestExecutor(ABC):
    @classmethod
    def log(
        cls,
        test_id: str,
        message: str,
        payload: dict | list[dict] = None,
        level: LogLevel = LogLevel.INFO,
    ):
        log_dto = LogDto(
            subject_type=LogSubjectType.TEST_EXECUTION,
            subject=test_id,
            message=message,
            level=level,
            payload=payload,
        )
        LogService().log(log_dto)
        publish_runtime_log_event(
            subject_type=LogSubjectType.TEST_EXECUTION,
            subject=test_id,
            level=level,
            message=message,
            payload=payload,
        )

    @classmethod
    def execute_operations(
        cls,
        session: Session,
        test_id: str,
        test_code: str,
        data,
    ) -> list[dict[str, str]]:
        test_operations = cls.find_all_operations(session, test_id)
        with bind_execution_context(suite_test_id=test_id):
            execution_result = execute_operations(session, test_operations, data)
        set_context_last(item_id=test_code, data=execution_result.data)
        return execution_result.result

    @classmethod
    def find_all_operations(cls, session: Session, test_id: str):
        return TestOperationService().get_all_by_test(session, test_id)

    @abstractmethod
    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: ConfigurationTestDtoTypes,
    ) -> list[dict[str, str]]:
        raise NotImplementedError


