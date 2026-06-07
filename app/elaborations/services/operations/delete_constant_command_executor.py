from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    DeleteConstantConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.constants.command_constant_definition_registry import (
    resolve_definition_path,
)
from elaborations.services.suite_runs.run_context import remove_context_path


class DeleteConstantOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DeleteConstantConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        definition, target_path = resolve_definition_path(
            session,
            cfg.targetRuntimeValueRef.definitionId,
        )
        remove_context_path(target_path)
        message = (
            f"Deleted constant '{definition.name}' from context "
            f"'{definition.context_scope}'."
        )
        self.log(operation_id, message)
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    "name": definition.name,
                    "context": definition.context_scope,
                }
            ],
        )

