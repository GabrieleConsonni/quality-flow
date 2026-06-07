from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    SetResponseBodyConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import set_response_body


class SetResponseBodyOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SetResponseBodyConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        set_response_body(cfg.body)
        message = "Response body updated"
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "body": cfg.body}])

