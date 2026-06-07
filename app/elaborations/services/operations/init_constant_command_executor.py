from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    ConstantSourceType,
    InitConstantConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path


class DataOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: InitConstantConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        resolved_value = self._load_value(session, cfg, data)
        target_path = f"$.{cfg.context}.constants.{cfg.name}"
        write_context_path(target_path, resolved_value)
        message = f"Initialized constant '{cfg.name}' in context '{cfg.context}'."
        self.log(
            operation_id,
            message=message,
            payload={
                "name": cfg.name,
                "context": cfg.context,
                "value_type": cfg.valueType,
            },
        )
        return ExecutionResultDto(
            data=resolved_value,
            result=[
                {
                    "message": message,
                    "name": cfg.name,
                    "context": cfg.context,
                    "valueType": cfg.valueType,
                }
            ],
        )

    def _load_value(self, session: Session, cfg: InitConstantConfigurationCommandDto, data):
        del session
        del data
        if cfg.valueType == ConstantSourceType.VALUE.value:
            return cfg.value
        if cfg.valueType == ConstantSourceType.JSON.value:
            return cfg.value
        if cfg.valueType == ConstantSourceType.FUNCTION.value:
            if cfg.functionName == "today":
                from datetime import date

                return date.today().isoformat()
            from datetime import UTC, datetime

            return datetime.now(UTC).replace(microsecond=0).isoformat()
        raise ValueError(f"Unsupported valueType '{cfg.valueType}' for setVariable.")

