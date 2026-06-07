from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    SetVarConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    set_context_var,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


class SetVarOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: SetVarConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del session
        scope = build_run_context_scope()
        resolved_value = resolve_dynamic_value(cfg.value, scope)
        set_context_var(cfg.key, resolved_value, scope=cfg.scope)
        self.log(
            operation_id,
            message=f"Set context var '{cfg.key}'",
            payload={"key": cfg.key, "value": resolved_value, "scope": cfg.scope},
        )
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": f"Context var '{cfg.key}' updated",
                    "key": cfg.key,
                    "value": resolved_value,
                    "scope": cfg.scope,
                }
            ],
        )

