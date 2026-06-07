from sqlalchemy.orm import Session

from _alembic.models.dataset_entity import DatasetEntity
from _alembic.models.json_payload_entity import JsonPayloadEntity
from data_sources.models.database_connection_config_types import DatabaseConnectionConfigTypes
from data_sources.models.database_connection_config_types import convert_database_connection_config
from data_sources.services.alembic.dataset_service import DatasetService
from elaborations.models.dtos.configuration_command_dto import ExportDatasetConfigurationCommandDto
from elaborations.services.operations.command_data_resolver import (
    coerce_rows,
    resolve_input_reference,
    write_result_constant,
)
from elaborations.services.operations.command_executor import OperationExecutor, ExecutionResultDto
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter
from sqlalchemy_utils.database_table_manager import DatabaseTableManager
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import create_sqlalchemy_engine


class SaveToExternalDbOperationExecutor(OperationExecutor):

    def execute(self, session:Session, operation_id:str, cfg: ExportDatasetConfigurationCommandDto, data)->ExecutionResultDto:
        connection_id = str(cfg.connection_id or "").strip()
        table_name = str(cfg.table_name or "").strip()
        input_data, _input_type = resolve_input_reference(session, cfg.inputRef, data)
        rows = coerce_rows(input_data)

        if not connection_id:
            raise ValueError("exportDataset requires connection_id.")
        if not table_name:
            raise ValueError("exportDataset requires table_name.")

        connection:DatabaseConnectionConfigTypes = self.load_database_connection(session, connection_id)

        engine = create_sqlalchemy_engine(connection)

        if not rows:
            message = f"No data to insert into {table_name} table"
            self.log(operation_id, message)
            return ExecutionResultDto(
                data=input_data,
                result=[{"message": message}]
            )

        if cfg.mode == "drop-create":
            DatabaseTableManager.drop_table(engine, table_name)

        sample_row = {}
        for d in rows:
            for key, value in d.items():
                sample_row[key] = value

        table = DatabaseTableWriter.ensure_table_exists(engine, table_name, sample_row)
        if cfg.mode == "insert-update" and cfg.mapping_keys:
            from sqlalchemy import text
            with engine.begin() as connection_handle:
                for row in rows:
                    predicates = []
                    params = {}
                    for index, key in enumerate(cfg.mapping_keys):
                        param_key = f"k{index}"
                        predicates.append(f"{key} = :{param_key}")
                        params[param_key] = row.get(key)
                    if predicates:
                        connection_handle.execute(text(f"DELETE FROM {table_name} WHERE " + " AND ".join(predicates)), params)
                DatabaseTableWriter.insert_rows(engine, table, rows)
        else:
            if cfg.mode == "drop-create":
                table = DatabaseTableWriter.ensure_table_exists(engine, table_name, sample_row)
            DatabaseTableWriter.insert_rows(engine, table, rows)

        schema_name = connection.db_schema or None
        if "." in table_name:
            schema_name, table_only = table_name.split(".", 1)
        else:
            table_only = table_name
        dataset_description = str(cfg.dataset_description or table_name)
        dataset_payload = {
            "connection_id": connection_id,
            "object_name": table_only,
            "object_type": "table",
        }
        if schema_name:
            dataset_payload["schema"] = schema_name
        if cfg.dataset_id:
            DatasetService().update(
                session,
                cfg.dataset_id,
                description=dataset_description,
                configuration_json=dataset_payload,
            )
            dataset_id = cfg.dataset_id
        else:
            dataset_id = DatasetService().insert(
                session,
                DatasetEntity(
                    description=dataset_description,
                    configuration_json=dataset_payload,
                    perimeter=None,
                ),
            )

        message = f"Created {len(rows)} rows in {table_name} table"
        result_payload = {
            "table_name": table_name,
            "inserted_rows": len(rows),
            "connection_id": connection_id,
            "dataset_id": dataset_id,
            "mode": cfg.mode,
        }
        if cfg.resultConstant:
            write_result_constant(session, cfg.resultConstant, result_payload)

        self.log(operation_id, message)

        return ExecutionResultDto(
            data=input_data,
            result=[{"message": message}]
        )

    def load_database_connection(self,session:Session, _id:str):
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, _id)

        if not json_payload_entity:
            raise ValueError(f"Database connection '{_id}' not found")

        return convert_database_connection_config(json_payload_entity.payload)

