from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from _alembic.services.alembic_config_service import url_from_env
from elaborations.models.dtos.configuration_command_dto import (
    CleanTableConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)


class CleanTableOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: CleanTableConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        del session
        engine = create_engine(url_from_env())
        with engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {cfg.table_name}"))
        message = f"Cleaned internal table '{cfg.table_name}'."
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "table_name": cfg.table_name}])

