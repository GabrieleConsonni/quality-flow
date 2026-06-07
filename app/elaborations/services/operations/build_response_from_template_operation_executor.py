from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    BuildResponseFromTemplateConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    set_response_body,
    set_response_header,
    set_response_status,
)


class BuildResponseFromTemplateOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: BuildResponseFromTemplateConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        if cfg.status is not None:
            set_response_status(cfg.status)
        if isinstance(cfg.headers, dict):
            for key, value in cfg.headers.items():
                set_response_header(str(key), value)
        if cfg.template is not None:
            set_response_body(cfg.template)
        message = "Response draft built from template"
        self.log(
            operation_id,
            message,
            payload={
                "status": cfg.status,
                "headers": cfg.headers if isinstance(cfg.headers, dict) else {},
            },
        )
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    "status": cfg.status,
                    "headers": cfg.headers if isinstance(cfg.headers, dict) else {},
                    "body": cfg.template,
                }
            ],
        )

