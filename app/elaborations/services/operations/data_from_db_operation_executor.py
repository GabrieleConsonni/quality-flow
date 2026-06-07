from sqlalchemy.orm import Session

from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import (
    DataFromDbConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path


class DataFromDbOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DataFromDbConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del data
        dataset = DatasetQueryService.get_dataset_or_raise_for_runtime(
            session,
            str(cfg.dataset_id or "").strip(),
        )
        rows = DatasetQueryService.load_rows_for_runtime(dataset)
        normalized_rows = rows if isinstance(rows, list) else []
        if cfg.target:
            write_context_path(cfg.target, normalized_rows)
        table_name = DatasetQueryService.qualified_table_name_from_dataset(dataset)
        self.log(operation_id, f"Loaded {len(rows)} row(s) from table '{table_name}'.")
        return ExecutionResultDto(
            data=normalized_rows,
            result=[{"message": f"Loaded {len(rows)} row(s) from table '{table_name}'."}],
        )

