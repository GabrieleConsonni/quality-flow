from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from elaborations.models.dtos.configuration_command_dto import (
    DataFromJsonArrayConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path
from json_utils.services.alembic.json_files_service import JsonFilesService


class DataFromJsonArrayOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DataFromJsonArrayConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del data
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(
            session,
            cfg.json_array_id,
        )
        if not json_payload_entity:
            raise ValueError(f"Json array '{cfg.json_array_id}' not found")
        payload = json_payload_entity.payload
        rows = payload if isinstance(payload, list) else [payload]
        if cfg.target:
            write_context_path(cfg.target, rows)
        self.log(operation_id, f"Loaded {len(rows)} row(s) from json array.")
        return ExecutionResultDto(
            data=rows,
            result=[{"message": f"Loaded {len(rows)} row(s) from json array."}],
        )

