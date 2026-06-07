from sqlalchemy.orm import Session

from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.services.alembic.dataset_service import DatasetService
from data_sources.services.alembic.database_connection_service import load_database_connection
from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import (
    DropDatasetConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from sqlalchemy_utils.database_table_manager import DatabaseTableManager
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)


class DropDatasetOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DropDatasetConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        entity = DatasetQueryService.get_dataset_or_raise_for_runtime(session, cfg.dataset_id)
        payload = (
            entity.configuration_json if isinstance(entity.configuration_json, dict) else {}
        )
        connection_id = str(payload.get("connection_id") or "").strip()
        table_name = self._table_name_from_payload(payload)
        database_connection_cfg: DatabaseConnectionConfigTypes = load_database_connection(connection_id)
        engine = create_sqlalchemy_engine(database_connection_cfg)
        DatabaseTableManager.drop_table(engine, table_name)
        DatasetService().delete_by_id(session, cfg.dataset_id)
        message = f"Dropped dataset '{cfg.dataset_id}' and table '{table_name}'."
        self.log(operation_id, message)
        return ExecutionResultDto(data=data, result=[{"message": message, "dataset_id": cfg.dataset_id}])

    @staticmethod
    def _table_name_from_payload(payload: dict) -> str:
        object_name = str(payload.get("object_name") or "").strip()
        schema = str(payload.get("schema") or "").strip()
        return object_name if not schema or "." in object_name else f"{schema}.{object_name}"

