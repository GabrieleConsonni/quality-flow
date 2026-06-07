from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    SetResponseHeaderConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import set_response_header


class SetResponseHeaderOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SetResponseHeaderConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        set_response_header(cfg.name, cfg.value)
        message = f"Response header '{cfg.name}' updated"
        self.log(
            operation_id,
            message,
            payload={"name": cfg.name, "value": cfg.value},
        )
        return ExecutionResultDto(
            data=data,
            result=[{"message": message, "name": cfg.name, "value": cfg.value}],
        )

