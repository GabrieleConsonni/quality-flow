import time

from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    SleepConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)


class SleepOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SleepConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        time.sleep(cfg.duration)
        self.log(operation_id, f"Slept for {cfg.duration} second(s).")
        return ExecutionResultDto(
            data=data,
            result=[{"message": f"Slept for {cfg.duration} second(s)."}],
        )

