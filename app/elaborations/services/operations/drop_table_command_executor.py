from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from _alembic.services.alembic_config_service import url_from_env
from elaborations.models.dtos.configuration_command_dto import (
    DropTableConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from sqlalchemy_utils.database_table_manager import DatabaseTableManager


class DropTableOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DropTableConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        del session
        engine = create_engine(url_from_env())
        DatabaseTableManager.drop_table(engine, cfg.table_name)
        message = f"Dropped internal table '{cfg.table_name}'."
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "table_name": cfg.table_name}])

