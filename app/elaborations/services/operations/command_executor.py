from abc import abstractmethod, ABC

from pydantic.dataclasses import dataclass
from sqlalchemy.orm import Session

from _alembic.services.session_context_manager import managed_session
from elaborations.models.dtos.configuration_command_dto import ConfigurationOperationTypes
from _alembic.models.log_entity import LogEntity
from elaborations.services.suite_runs.execution_event_bus import publish_runtime_log_event
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService


@dataclass
class ExecutionResultDto:
    data: object
    result: list[dict[str, object]]

    def extend(self, new_result):
        self.data = new_result.data
        self.result.extend(new_result.result)


class OperationExecutor(ABC):
    @classmethod
    def log(cls, operation_id: str, message: str, payload: dict | list[dict] = None, level: LogLevel = LogLevel.INFO):
        log_dto = LogDto(
            subject_type=LogSubjectType.OPERATION_EXECUTION,
            subject=operation_id,
            message=message,
            level=level,
            payload=payload
        )
        LogService().log(log_dto)
        publish_runtime_log_event(
            subject_type=LogSubjectType.OPERATION_EXECUTION,
            subject=operation_id,
            level=level,
            message=message,
            payload=payload,
        )

    @abstractmethod
    def execute(self, session: Session, operation_id: str, op: ConfigurationOperationTypes,
                data) -> ExecutionResultDto:
        pass

